from __future__ import annotations

import time
from typing import Any


class OpenSessions:
    def __init__(self, limit: int, idle_seconds: float) -> None:
        self.limit = limit
        self.idle_seconds = idle_seconds
        self._open: dict[str, dict[str, float]] = {}

    def allow(self, identity: str, session_id: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        held = {
            sid: seen
            for sid, seen in self._open.get(identity, {}).items()
            if now - seen < self.idle_seconds
        }
        if session_id not in held and len(held) >= self.limit:
            return False
        held[session_id] = now
        self._open[identity] = held
        return True

    def release(self, identity: str, session_id: str) -> None:
        held = self._open.get(identity)
        if not held:
            return
        held.pop(session_id, None)
        if not held:
            self._open.pop(identity, None)


def caller_identity(body: dict[str, Any]) -> str:
    """Yandex account, or the device when Dialogs sent no account id."""
    session = body.get("session") if isinstance(body.get("session"), dict) else {}
    user = session.get("user") if isinstance(session.get("user"), dict) else {}
    application = session.get("application") if isinstance(session.get("application"), dict) else {}
    user_id = user.get("user_id") or session.get("user_id")
    if isinstance(user_id, str) and user_id.strip():
        return "user:" + user_id.strip()
    application_id = application.get("application_id")
    if isinstance(application_id, str) and application_id.strip():
        return "app:" + application_id.strip()
    return ""


def open_session_limit_text(limit: int) -> str:
    return f"Превышен лимит открытых сессий. Лимит открытых сессий: {limit}."
