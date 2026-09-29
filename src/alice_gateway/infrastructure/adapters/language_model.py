from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import httpx

from alice_gateway.service.ports.language_model import ChatMessage, LanguageModel, LanguageModelError

logger = logging.getLogger(__name__)

# Request model name is ignored by an AI Agent endpoint: the agent uses its own model.
DEFAULT_TIMEWEB_MODEL = "deepseek-v4-flash"
_CHAT_COMPLETIONS_SUFFIX = "/chat/completions"


def normalize_openai_compatible_root(base_url: str) -> str:
    """Return an OpenAI-compatible API root without a trailing /chat/completions."""
    root = base_url.strip().rstrip("/")
    if root.endswith(_CHAT_COMPLETIONS_SUFFIX):
        root = root[: -len(_CHAT_COMPLETIONS_SUFFIX)].rstrip("/")
    return root


def message_body(*, model: str, messages: Sequence[ChatMessage]) -> dict[str, Any]:
    # Omit temperature and max_tokens. GPT-5 family agents reject them.
    # Sampling and length stay on the agent, so swapping agents does not require a code change.
    return {
        "model": model,
        "stream": False,
        "messages": list(messages),
    }


class StubLanguageModel(LanguageModel):
    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        return "Языковая модель не настроена. Укажите TIMEWEB_API_KEY и TIMEWEB_BASE_URL и перезапустите сервис."


class TimewebLanguageModel(LanguageModel):
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str = DEFAULT_TIMEWEB_MODEL,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("TIMEWEB_API_KEY is required")
        if not base_url.strip():
            raise ValueError("TIMEWEB_BASE_URL is required")
        self._api_key = api_key
        self._base_url = normalize_openai_compatible_root(base_url)
        if not self._base_url:
            raise ValueError("TIMEWEB_BASE_URL is required")
        self._model = model
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
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        client = await self._http()
        try:
            response = await client.post(
                self.chat_completions_url,
                headers=self._headers(),
                json=message_body(model=self._model, messages=messages),
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("language model request failed: %s", exc.__class__.__name__)
            raise LanguageModelError("language model request failed") from exc
        payload = response.json()
        content = _content_from_payload(payload)
        if not content:
            raise LanguageModelError("language model returned empty content")
        return content


def _content_from_payload(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        return ""
    return content.strip()
