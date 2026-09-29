from __future__ import annotations

from alice_gateway.service.models.commands.base import Command, CommandResult


class ReplyToUtteranceCommand(Command):
    session_id: str
    session_new: bool
    utterance: str
    action: str | None = None
    dangerous: bool = False
    request_type: str = "SimpleUtterance"


class ReplyToUtteranceResult(CommandResult):
    text: str
    end_session: bool = False
    suggest_continue: bool = False
