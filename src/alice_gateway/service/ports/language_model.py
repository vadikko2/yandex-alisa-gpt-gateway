from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import NotRequired, Protocol, TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str
    reasoning_content: NotRequired[str]


@dataclass(frozen=True)
class ModelCompletion:
    """Assistant turn to speak and, on DeepSeek with tools, to send back next time."""

    text: str
    reasoning_content: str | None = None


class LanguageModel(Protocol):
    async def complete(self, messages: Sequence[ChatMessage]) -> ModelCompletion:
        """Return the assistant text for a chat transcript."""


class LanguageModelError(Exception):
    """The configured model endpoint failed or returned nothing usable."""
