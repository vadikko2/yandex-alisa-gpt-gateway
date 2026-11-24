from __future__ import annotations

import asyncio
import ipaddress
import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from alice_gateway.infrastructure.adapters.language_model import (
    OpenAICompatibleLanguageModel,
    deepseek_web_search,
    message_body,
    normalize_openai_compatible_root,
)
from alice_gateway.infrastructure.dialogs import DialogStore
from alice_gateway.presentation.main import (
    _PUBLISHED_YANDEX_NETWORKS,
    configure_logging,
    create_app,
    yandex_networks,
)
from alice_gateway.presentation.open_sessions import OpenSessions, open_session_limit_text
from alice_gateway.presentation.protocol import alice_response, command_from_body
from alice_gateway.service.handlers.commands.reply import (
    WELCOME_TEXT,
    ReplyToUtteranceCommandHandler,
    fit_alice_text,
)
from alice_gateway.service.models.commands.reply import ReplyToUtteranceCommand, ReplyToUtteranceResult
from alice_gateway.service.ports.language_model import ModelCompletion
from alice_gateway.shared.settings import Settings, load_settings, read_system_prompt


class ScriptedLanguageModel:
    def __init__(self, text: str, delay: float = 0, reasoning_content: str | None = None) -> None:
        self.text = text
        self.delay = delay
        self.reasoning_content = reasoning_content
        self.seen: list[list[dict[str, str]]] = []

    async def complete(self, messages: list[dict[str, str]]) -> ModelCompletion:
        self.seen.append(list(messages))
        if self.delay:
            await asyncio.sleep(self.delay)
        return ModelCompletion(text=self.text, reasoning_content=self.reasoning_content)


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "llm_api_key": "test-key",
        "llm_base_url": "https://api.example/v1",
        "alice_reply_budget_seconds": 2,
        "system_prompt": "test system prompt",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _skip_live_yandex_ip_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    async def refresh() -> None:
        return None

    monkeypatch.setattr("alice_gateway.presentation.main._refresh_yandex_ips", refresh)
    yandex_networks[:] = [ipaddress.ip_network("203.0.113.0/24")]
    yield
    yandex_networks.clear()


def _handler(model: ScriptedLanguageModel, settings: Settings | None = None) -> ReplyToUtteranceCommandHandler:
    return ReplyToUtteranceCommandHandler(
        language_model=model,
        dialogs=DialogStore(),
        settings=settings or _settings(),
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://api.deepseek.com", "https://api.deepseek.com"),
        ("https://api.deepseek.com/", "https://api.deepseek.com"),
        ("https://api.example/v1/chat/completions", "https://api.example/v1"),
    ],
)
def test_normalize_openai_compatible_root(raw: str, expected: str) -> None:
    assert normalize_openai_compatible_root(raw) == expected


def test_message_body_omits_sampling_params() -> None:
    body = message_body(model="deepseek-flash", messages=[{"role": "user", "content": "привет"}])
    assert "temperature" not in body
    assert "max_tokens" not in body
    assert body["stream"] is False
    assert "tools" not in body


def test_deepseek_request_searches_while_thinking() -> None:
    assert deepseek_web_search("https://api.deepseek.com")
    assert deepseek_web_search("https://api.deepseek.com/v1/chat/completions")
    assert not deepseek_web_search("https://api.example/v1")
    body = message_body(
        model="deepseek-flash",
        messages=[{"role": "user", "content": "погода"}],
        web_search=True,
    )
    assert body["thinking"] == {"type": "enabled"}
    assert body["tools"] == [{"type": "deepseek_web_search"}]


def test_chat_completions_url_uses_the_configured_root() -> None:
    first = OpenAICompatibleLanguageModel(api_key="key-a", base_url="https://api.deepseek.com")
    second = OpenAICompatibleLanguageModel(api_key="key-b", base_url="https://api.example/v1/chat/completions")
    assert first.chat_completions_url == "https://api.deepseek.com/chat/completions"
    assert second.chat_completions_url == "https://api.example/v1/chat/completions"


@pytest.mark.asyncio
async def test_openai_compatible_client_posts_bearer_and_reads_content() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"choices": [{"message": {"content": "  готово  "}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model = OpenAICompatibleLanguageModel(api_key="secret", base_url="https://api.deepseek.com", client=client)
    completion = await model.complete([{"role": "user", "content": "привет"}])
    await client.aclose()
    assert completion.text == "готово"
    assert completion.reasoning_content == ""
    assert seen["auth"] == "Bearer secret"
    assert seen["body"]["model"] == "deepseek-flash"
    assert seen["body"]["thinking"] == {"type": "enabled"}
    assert seen["body"]["tools"] == [{"type": "deepseek_web_search"}]
    assert seen["body"]["messages"][0]["content"] == "привет"


@pytest.mark.asyncio
async def test_deepseek_completion_keeps_reasoning_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": " в Москве ясно ",
                            "reasoning_content": "проверил погоду",
                        },
                    },
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model = OpenAICompatibleLanguageModel(api_key="secret", base_url="https://api.deepseek.com", client=client)
    completion = await model.complete([{"role": "user", "content": "погода"}])
    await client.aclose()
    assert completion.text == "в Москве ясно"
    assert completion.reasoning_content == "проверил погоду"


@pytest.mark.asyncio
async def test_other_provider_drops_reasoning_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ок", "reasoning_content": "не нужно"}}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model = OpenAICompatibleLanguageModel(api_key="secret", base_url="https://api.example/v1", client=client)
    completion = await model.complete([{"role": "user", "content": "привет"}])
    await client.aclose()
    assert completion.text == "ок"
    assert completion.reasoning_content is None


@pytest.mark.asyncio
async def test_status_error_includes_response_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"message": "The reasoning_content in the thinking mode must be passed back to the API."}},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model = OpenAICompatibleLanguageModel(api_key="secret", base_url="https://api.deepseek.com", client=client)
    with pytest.raises(Exception, match="reasoning_content") as caught:
        await model.complete([{"role": "user", "content": "ещё"}])
    await client.aclose()
    assert "HTTP 400" in str(caught.value)


@pytest.mark.asyncio
async def test_follow_up_sends_previous_reasoning_content() -> None:
    model = ScriptedLanguageModel("Ответ раз", reasoning_content="думал")
    handler = _handler(model)
    await handler.handle(ReplyToUtteranceCommand(session_id="s1", session_new=True, utterance="Привет"))
    await handler.handle(ReplyToUtteranceCommand(session_id="s1", session_new=False, utterance="Ещё"))
    assistant = model.seen[1][2]
    assert assistant == {"role": "assistant", "content": "Ответ раз", "reasoning_content": "думал"}


def test_fit_alice_text_cuts_on_a_sentence() -> None:
    text = ("Коротко. " * 200).strip()
    fitted = fit_alice_text(text)
    assert len(fitted) <= 1024
    assert fitted.endswith(".")


@pytest.mark.asyncio
async def test_new_session_without_text_welcomes_without_calling_the_model() -> None:
    model = ScriptedLanguageModel("не должен вызваться")
    handler = _handler(model)
    result = await handler.handle(ReplyToUtteranceCommand(session_id="s1", session_new=True, utterance=""))
    assert result.text == WELCOME_TEXT
    assert result.end_session is False
    assert model.seen == []


@pytest.mark.asyncio
async def test_stop_phrase_ends_the_session() -> None:
    handler = _handler(ScriptedLanguageModel("нет"))
    result = await handler.handle(ReplyToUtteranceCommand(session_id="s1", session_new=False, utterance="Хватит."))
    assert result.end_session is True
    assert result.text == "До свидания."


@pytest.mark.asyncio
async def test_fast_answer_is_returned_and_kept_in_the_transcript() -> None:
    model = ScriptedLanguageModel("Ответ раз")
    handler = _handler(model)
    first = await handler.handle(ReplyToUtteranceCommand(session_id="s1", session_new=True, utterance="Привет"))
    second = await handler.handle(ReplyToUtteranceCommand(session_id="s1", session_new=False, utterance="Ещё"))
    assert first.text == "Ответ раз"
    assert second.text == "Ответ раз"
    roles = [message["role"] for message in model.seen[1]]
    assert roles == ["system", "user", "assistant", "user"]


@pytest.mark.asyncio
async def test_slow_model_asks_to_continue_and_then_delivers() -> None:
    model = ScriptedLanguageModel("Поздний ответ", delay=0.2)
    handler = _handler(model, _settings(alice_reply_budget_seconds=0.05))
    waiting = await handler.handle(ReplyToUtteranceCommand(session_id="s1", session_new=False, utterance="Вопрос"))
    assert waiting.suggest_continue is True
    assert waiting.end_session is False
    await asyncio.sleep(0.3)
    delivered = await handler.handle(
        ReplyToUtteranceCommand(session_id="s1", session_new=False, utterance="дальше", action="continue"),
    )
    assert delivered.text == "Поздний ответ"
    assert delivered.suggest_continue is False


def test_alice_response_shape() -> None:
    payload = alice_response(ReplyToUtteranceResult(text="Привет", suggest_continue=True))
    assert payload["version"] == "1.0"
    assert payload["response"]["text"] == "Привет"
    assert payload["response"]["end_session"] is False
    assert payload["response"]["buttons"][0]["title"] == "Дальше"
    command = command_from_body(
        {
            "session": {"session_id": "abc", "new": True},
            "request": {"type": "SimpleUtterance", "original_utterance": "привет", "command": "привет"},
        },
    )
    assert command.session_id == "abc"
    assert command.session_new is True
    assert command.utterance == "привет"


def test_health_and_welcome_over_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")
    with TestClient(create_app()) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
        welcome = client.post(
            "/alice",
            headers={"x-forwarded-for": "203.0.113.9"},
            json={
                "version": "1.0",
                "session": {"session_id": "web", "new": True, "message_id": 0, "skill_id": "skill"},
                "request": {"type": "SimpleUtterance", "command": "", "original_utterance": ""},
            },
        )
        assert welcome.status_code == 200
        body = welcome.json()
        assert body["response"]["text"] == WELCOME_TEXT
        assert body["response"]["end_session"] is False
        assert body["version"] == "1.0"


def test_system_prompt_is_loaded_from_markdown_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompt_file = tmp_path / "custom.md"
    prompt_file.write_text("Кастомный system prompt\n", encoding="utf-8")
    monkeypatch.setenv("SYSTEM_PROMPT_PATH", str(prompt_file))
    settings = load_settings(base_dir=tmp_path)
    assert settings.system_prompt == "Кастомный system prompt"
    assert "Кастомный" in read_system_prompt(prompt_file)


def test_configure_logging_quiets_http_client_and_stamps_time() -> None:
    logging.getLogger("cqrs").setLevel(logging.DEBUG)
    configure_logging()
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
    assert logging.getLogger("cqrs").level == logging.NOTSET
    assert not logging.getLogger("cqrs").isEnabledFor(logging.DEBUG)
    record = logging.LogRecord("alice", logging.INFO, __file__, 1, "POST /alice 200", (), None)
    rendered = logging.getLogger().handlers[0].format(record)
    assert rendered.endswith("INFO POST /alice 200")
    assert rendered[:4].isdigit()


def test_successful_alice_hit_logs_caller_and_address(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")
    payload = {
        "version": "1.0",
        "session": {
            "session_id": "web",
            "new": True,
            "user": {"user_id": "user-1"},
            "application": {"application_id": "app-1"},
        },
        "request": {
            "type": "SimpleUtterance",
            "command": "какая погода",
            "original_utterance": "какая погода\nсейчас",
        },
    }
    with caplog.at_level(logging.INFO, logger="alice_gateway.presentation.main"):
        with TestClient(create_app()) as client:
            health = client.get("/health")
            welcome = client.post(
                "/alice",
                json=payload,
                headers={"x-forwarded-for": "203.0.113.9, 10.0.0.2"},
            )
    assert health.status_code == 200
    assert welcome.status_code == 200
    hits = [record.getMessage() for record in caplog.records if record.name == "alice_gateway.presentation.main"]
    assert len(hits) == 1
    message = hits[0]
    assert message.startswith("POST /alice 200 ")
    assert "user=user-1" in message
    assert "app=app-1" in message
    assert "ip=203.0.113.9" in message
    assert "session=web" in message
    assert "ms=" in message
    assert 'text="какая погода сейчас"' in message


def test_published_yandex_ranges_include_dialogs_console() -> None:
    networks = [ipaddress.ip_network(item) for item in _PUBLISHED_YANDEX_NETWORKS]
    assert any(ipaddress.ip_address("5.45.207.40") in network for network in networks)
    assert any(ipaddress.ip_address("5.45.207.48") in network for network in networks)


def test_alice_rejects_address_outside_yandex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")
    with TestClient(create_app()) as client:
        denied = client.post(
            "/alice",
            headers={"x-forwarded-for": "198.51.100.4"},
            json={"session": {"session_id": "x", "new": True}, "request": {}},
        )
        health = client.get("/health")
    assert denied.status_code == 200
    assert denied.json() == {
        "response": {"text": "Запрос должен быть с адресов Яндекса.", "end_session": True},
        "version": "1.0",
    }
    assert health.status_code == 200


def _alice_turn(
    client: TestClient,
    session_id: str,
    *,
    user_id: str | None = "user-1",
    application_id: str | None = None,
    text: str = "",
    new: bool = True,
    forwarded_for: str = "203.0.113.9",
):
    session: dict[str, object] = {"session_id": session_id, "new": new, "message_id": 0, "skill_id": "skill"}
    if user_id is not None:
        session["user"] = {"user_id": user_id}
    if application_id is not None:
        session["application"] = {"application_id": application_id}
    return client.post(
        "/alice",
        headers={"x-forwarded-for": forwarded_for},
        json={
            "version": "1.0",
            "session": session,
            "request": {"type": "SimpleUtterance", "command": text, "original_utterance": text},
        },
    )


def test_open_session_slot_frees_on_idle_and_on_close() -> None:
    sessions = OpenSessions(1, 10)
    assert sessions.allow("user:1", "a", now=0)
    assert sessions.allow("user:1", "a", now=9)
    assert not sessions.allow("user:1", "b", now=9)
    sessions.release("user:1", "a")
    assert sessions.allow("user:1", "b", now=9)
    assert sessions.allow("user:1", "c", now=19)


def test_second_open_session_is_told_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")
    monkeypatch.setenv("MAX_OPEN_SESSIONS", "1")
    with TestClient(create_app()) as client:
        first = _alice_turn(client, "s-a")
        other_user = _alice_turn(client, "s-c", user_id="user-2")
        second = _alice_turn(client, "s-b")
        continued = _alice_turn(client, "s-a", new=False, text="ещё")
    assert first.status_code == 200
    assert first.json()["response"]["text"] == WELCOME_TEXT
    assert other_user.json()["response"]["text"] == WELCOME_TEXT
    assert second.status_code == 200
    assert second.json() == {
        "response": {"text": open_session_limit_text(1), "end_session": True},
        "version": "1.0",
    }
    assert continued.json()["response"]["end_session"] is False
    assert continued.json()["response"]["text"] != open_session_limit_text(1)


def test_ended_session_frees_the_open_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")
    monkeypatch.setenv("MAX_OPEN_SESSIONS", "1")
    with TestClient(create_app()) as client:
        _alice_turn(client, "s-a")
        stopped = _alice_turn(client, "s-a", new=False, text="хватит")
        restarted = _alice_turn(client, "s-b")
    assert stopped.json()["response"]["end_session"] is True
    assert restarted.json()["response"]["text"] == WELCOME_TEXT


def test_open_session_limit_uses_the_device_without_an_account(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")
    monkeypatch.setenv("MAX_OPEN_SESSIONS", "1")
    with TestClient(create_app()) as client:
        phone = _alice_turn(client, "phone-1", user_id=None, application_id="phone")
        phone_again = _alice_turn(client, "phone-2", user_id=None, application_id="phone")
        station = _alice_turn(client, "station-1", user_id=None, application_id="station")
    assert phone.json()["response"]["text"] == WELCOME_TEXT
    assert phone_again.json()["response"]["text"] == open_session_limit_text(1)
    assert station.json()["response"]["text"] == WELCOME_TEXT


def test_open_session_limit_follows_the_account_across_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")
    monkeypatch.setenv("MAX_OPEN_SESSIONS", "1")
    with TestClient(create_app()) as client:
        phone = _alice_turn(client, "phone", application_id="phone")
        station = _alice_turn(client, "station", application_id="station")
    assert phone.json()["response"]["text"] == WELCOME_TEXT
    assert station.json()["response"]["text"] == open_session_limit_text(1)


def test_alice_without_a_caller_id_is_not_session_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")
    monkeypatch.setenv("MAX_OPEN_SESSIONS", "1")
    with TestClient(create_app()) as client:
        first = _alice_turn(client, "anon-1", user_id=None)
        second = _alice_turn(client, "anon-2", user_id=None)
    assert first.json()["response"]["text"] == WELCOME_TEXT
    assert second.json()["response"]["text"] == WELCOME_TEXT


def test_open_session_limit_text_includes_the_configured_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")
    monkeypatch.setenv("MAX_OPEN_SESSIONS", "2")
    with TestClient(create_app()) as client:
        first = _alice_turn(client, "s-1")
        second = _alice_turn(client, "s-2")
        third = _alice_turn(client, "s-3")
    assert first.json()["response"]["text"] == WELCOME_TEXT
    assert second.json()["response"]["text"] == WELCOME_TEXT
    assert third.json() == {
        "response": {"text": open_session_limit_text(2), "end_session": True},
        "version": "1.0",
    }


def test_address_outside_yandex_does_not_take_an_open_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")
    monkeypatch.setenv("MAX_OPEN_SESSIONS", "1")
    with TestClient(create_app()) as client:
        forged = _alice_turn(client, "forged", forwarded_for="198.51.100.4")
        opened = _alice_turn(client, "real")
        extra = _alice_turn(client, "real-2")
    assert forged.json()["response"]["text"] == "Запрос должен быть с адресов Яндекса."
    assert opened.json()["response"]["text"] == WELCOME_TEXT
    assert extra.json()["response"]["text"] == open_session_limit_text(1)
