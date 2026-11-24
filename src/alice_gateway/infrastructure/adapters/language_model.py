from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlparse

import httpx

from alice_gateway.service.ports.language_model import (
    ChatMessage,
    LanguageModel,
    LanguageModelError,
    ModelCompletion,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-flash"
_CHAT_COMPLETIONS_SUFFIX = "/chat/completions"
_DEEPSEEK_HOST = "api.deepseek.com"


def normalize_openai_compatible_root(base_url: str) -> str:
    """Return an OpenAI-compatible API root without a trailing /chat/completions."""
    root = base_url.strip().rstrip("/")
    if root.endswith(_CHAT_COMPLETIONS_SUFFIX):
        root = root[: -len(_CHAT_COMPLETIONS_SUFFIX)].rstrip("/")
    return root


def deepseek_web_search(base_url: str) -> bool:
    return (urlparse(normalize_openai_compatible_root(base_url)).hostname or "") == _DEEPSEEK_HOST


def message_body(
    *,
    model: str,
    messages: Sequence[ChatMessage],
    web_search: bool = False,
) -> dict[str, Any]:
    # Chat completions for every provider. Sampling stays on the provider.
    # On DeepSeek, thinking stays on: the model can search, open pages and check facts.
    body: dict[str, Any] = {
        "model": model,
        "stream": False,
        "messages": list(messages),
    }
    if web_search:
        body["thinking"] = {"type": "enabled"}
        body["tools"] = [{"type": "deepseek_web_search"}]
    return body


class StubLanguageModel(LanguageModel):
    async def complete(self, messages: Sequence[ChatMessage]) -> ModelCompletion:
        return ModelCompletion(text="Языковая модель не настроена. Укажите LLM_API_KEY и перезапустите сервис.")


class OpenAICompatibleLanguageModel(LanguageModel):
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("LLM_API_KEY is required")
        if not base_url.strip():
            raise ValueError("LLM_BASE_URL is required")
        self._api_key = api_key
        self._base_url = normalize_openai_compatible_root(base_url)
        if not self._base_url:
            raise ValueError("LLM_BASE_URL is required")
        self._model = model
        self._web_search = deepseek_web_search(self._base_url)
        self._client = client
        self._owns_client = client is None

    @property
    def chat_completions_url(self) -> str:
        return f"{self._base_url}{_CHAT_COMPLETIONS_SUFFIX}"

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def complete(self, messages: Sequence[ChatMessage]) -> ModelCompletion:
        client = await self._http()
        try:
            response = await client.post(
                self.chat_completions_url,
                headers=self._headers(),
                json=message_body(model=self._model, messages=messages, web_search=self._web_search),
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            detail = _error_detail(exc)
            logger.warning("language model request failed: %s", detail)
            raise LanguageModelError(f"language model request failed: {detail}") from exc
        text, reasoning = _message_from_payload(response.json())
        if not text:
            raise LanguageModelError("language model returned empty content")
        # With tools declared, DeepSeek returns 400 on the next turn unless every
        # earlier assistant message carries reasoning_content. An empty string is
        # accepted when that turn had none.
        if self._web_search:
            reasoning = reasoning or ""
        else:
            reasoning = None
        return ModelCompletion(text=text, reasoning_content=reasoning)


def _error_detail(exc: httpx.HTTPError) -> str:
    if not isinstance(exc, httpx.HTTPStatusError):
        return exc.__class__.__name__
    body = " ".join(exc.response.text.split())
    if len(body) > 500:
        body = body[:500] + "…"
    return f"HTTP {exc.response.status_code} {body}".strip()


def _message_from_payload(payload: dict[str, Any]) -> tuple[str, str | None]:
    choices = payload.get("choices") or []
    if not choices:
        return "", None
    message = choices[0].get("message") or {}
    content = message.get("content")
    text = content.strip() if isinstance(content, str) else ""
    reasoning = message.get("reasoning_content")
    if reasoning is None:
        return text, None
    if not isinstance(reasoning, str):
        return text, ""
    return text, reasoning
