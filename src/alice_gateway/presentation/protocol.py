from __future__ import annotations

from typing import Any

from alice_gateway.service.models.commands.reply import ReplyToUtteranceCommand, ReplyToUtteranceResult

_CONTINUE_BUTTON = {"title": "Дальше", "payload": {"action": "continue"}, "hide": True}
_STOP_BUTTON = {"title": "Закончить", "payload": {"action": "stop"}, "hide": True}


def command_from_body(body: dict[str, Any]) -> ReplyToUtteranceCommand:
    session = body.get("session") if isinstance(body.get("session"), dict) else {}
    request = body.get("request") if isinstance(body.get("request"), dict) else {}
    payload = request.get("payload") if isinstance(request.get("payload"), dict) else {}
    action = payload.get("action")
    utterance = request.get("original_utterance") or request.get("command") or ""
    markup = request.get("markup") if isinstance(request.get("markup"), dict) else {}
    return ReplyToUtteranceCommand(
        session_id=str(session.get("session_id") or "unknown"),
        session_new=bool(session.get("new")),
        utterance=str(utterance),
        action=str(action) if isinstance(action, str) else None,
        dangerous=bool(markup.get("dangerous_context")),
        request_type=str(request.get("type") or "SimpleUtterance"),
    )


def alice_response(result: ReplyToUtteranceResult) -> dict[str, Any]:
    response: dict[str, Any] = {
        "text": result.text,
        "end_session": result.end_session,
    }
    if not result.end_session:
        buttons = [_CONTINUE_BUTTON, _STOP_BUTTON] if result.suggest_continue else [_STOP_BUTTON]
        response["buttons"] = buttons
    return {"response": response, "version": "1.0"}
