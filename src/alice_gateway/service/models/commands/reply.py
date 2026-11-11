from __future__ import annotations

from alice_gateway.service.models.commands.base import Command, CommandResult


class ReplyToUtteranceResult(CommandResult):
    text: str
    end_session: bool = False
    suggest_continue: bool = False


class ReplyToUtteranceCommand(Command[ReplyToUtteranceResult]):
    session_id: str
    session_new: bool
    utterance: str
    action: str | None = None
    dangerous: bool = False
    request_type: str = "SimpleUtterance"
