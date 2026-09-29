from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from alice_gateway.infrastructure.adapters.language_model import (
    TimewebLanguageModel,
    message_body,
    normalize_openai_compatible_root,
)
from alice_gateway.infrastructure.dialogs import DialogStore
from alice_gateway.presentation.main import create_app
from alice_gateway.presentation.protocol import alice_response, command_from_body
from alice_gateway.service.handlers.commands.reply import (
    WELCOME_TEXT,
    ReplyToUtteranceCommandHandler,
    fit_alice_text,
)
from alice_gateway.service.models.commands.reply import ReplyToUtteranceCommand, ReplyToUtteranceResult
from alice_gateway.shared.settings import Settings


class ScriptedLanguageModel:
    def __init__(self, text: str, delay: float = 0) -> None:
        self.text = text
        self.delay = delay
        self.seen: list[list[dict[str, str]]] = []

    async def complete(self, messages: list[dict[str, str]]) -> str:
        self.seen.append(list(messages))
        if self.delay:
            await asyncio.sleep(self.delay)
        return self.text


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "timeweb_api_key": "test-key",
        "timeweb_base_url": "https://agent.example/v1",
        "alice_reply_budget_seconds": 2,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def _handler(model: ScriptedLanguageModel, settings: Settings | None = None) -> ReplyToUtteranceCommandHandler:
    return ReplyToUtteranceCommandHandler(
        language_model=model,
        dialogs=DialogStore(),
        settings=settings or _settings(),
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://agent.example/v1", "https://agent.example/v1"),
        ("https://agent.example/v1/", "https://agent.example/v1"),
        ("https://agent.example/v1/chat/completions", "https://agent.example/v1"),
    ],
)
def test_normalize_openai_compatible_root(raw: str, expected: str) -> None:
    assert normalize_openai_compatible_root(raw) == expected


def test_message_body_omits_sampling_params() -> None:
    body = message_body(model="deepseek-v4-flash", messages=[{"role": "user", "content": "привет"}])
    assert "temperature" not in body
    assert "max_tokens" not in body
    assert body["stream"] is False


def test_chat_completions_url_follows_the_configured_agent() -> None:
    first = TimewebLanguageModel(
        api_key="key-a",
        base_url="https://agent.timeweb.cloud/api/v1/cloud-ai/agents/agent-a/v1",
    )
    second = TimewebLanguageModel(
        api_key="key-b",
        base_url="https://agent.timeweb.cloud/api/v1/cloud-ai/agents/agent-b/v1/chat/completions",
    )
    assert first.chat_completions_url.endswith("/agents/agent-a/v1/chat/completions")
    assert second.chat_completions_url.endswith("/agents/agent-b/v1/chat/completions")


@pytest.mark.asyncio
async def test_timeweb_adapter_posts_bearer_and_reads_content() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"choices": [{"message": {"content": "  готово  "}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model = TimewebLanguageModel(api_key="secret", base_url="https://agent.example/v1", client=client)
    text = await model.complete([{"role": "user", "content": "привет"}])
    await client.aclose()
    assert text == "готово"
    assert seen["auth"] == "Bearer secret"
    assert seen["body"]["messages"][0]["content"] == "привет"


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
    monkeypatch.setenv("TIMEWEB_API_KEY", "")
    monkeypatch.setenv("TIMEWEB_BASE_URL", "")
    with TestClient(create_app()) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
        welcome = client.post(
            "/alice",
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
