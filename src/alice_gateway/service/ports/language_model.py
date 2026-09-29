from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


class LanguageModel(Protocol):
    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        """Return the assistant text for a chat transcript."""


class LanguageModelError(Exception):
    """The configured model endpoint failed or returned nothing usable."""
