from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from alice_gateway.service.ports.language_model import ModelCompletion


@dataclass
class Dialog:
    messages: list[dict[str, str]] = field(default_factory=list)
    pending: asyncio.Task[ModelCompletion] | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class DialogStore:
    """In-process transcript for one App instance.

    Alice session state is too small for a chat transcript, and this process
    keeps one in-memory store. A new deploy starts empty.
    """

    def __init__(self, *, max_sessions: int = 200, max_messages: int = 8) -> None:
        self._max_sessions = max_sessions
        self._max_messages = max_messages
        self._items: dict[str, Dialog] = {}
        self._order: list[str] = []

    def get(self, session_id: str) -> Dialog:
        dialog = self._items.get(session_id)
        if dialog is None:
            dialog = Dialog()
            self._items[session_id] = dialog
            self._order.append(session_id)
            self._evict()
        return dialog

    def reset(self, session_id: str) -> Dialog:
        previous = self._items.get(session_id)
        if previous is not None and previous.pending is not None and not previous.pending.done():
            previous.pending.cancel()
        dialog = Dialog()
        self._items[session_id] = dialog
        if session_id not in self._order:
            self._order.append(session_id)
        return dialog

    def trim(self, dialog: Dialog) -> None:
        overflow = len(dialog.messages) - self._max_messages
        if overflow > 0:
            del dialog.messages[:overflow]
        # DeepSeek rejects a transcript whose first turn is assistant:
        # "an assistant message must follow a user message".
        while dialog.messages and dialog.messages[0].get("role") != "user":
            del dialog.messages[0]

    def _evict(self) -> None:
        while len(self._order) > self._max_sessions:
            oldest = self._order.pop(0)
            dialog = self._items.pop(oldest, None)
            if dialog is not None and dialog.pending is not None and not dialog.pending.done():
                dialog.pending.cancel()
