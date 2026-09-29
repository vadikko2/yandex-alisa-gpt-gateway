from __future__ import annotations

import asyncio
import logging

import cqrs

from alice_gateway.infrastructure.dialogs import Dialog, DialogStore
from alice_gateway.service.models.commands.reply import ReplyToUtteranceCommand, ReplyToUtteranceResult
from alice_gateway.service.ports.language_model import ChatMessage, LanguageModel, LanguageModelError
from alice_gateway.shared.settings import Settings

logger = logging.getLogger(__name__)

ALICE_TEXT_LIMIT = 1024
WELCOME_TEXT = "Привет. Спросите что угодно. Чтобы закончить, скажите «хватит»."
WAIT_TEXT = "Думаю. Скажите «дальше», когда будете готовы."
EMPTY_TEXT = "Я не расслышала. Повторите, пожалуйста."
DANGEROUS_TEXT = "Не могу обсуждать это. Спросите о чём-нибудь другом."
UNSUPPORTED_TEXT = "Этот вид сообщения я пока не понимаю."
ERROR_TEXT = "Не получилось получить ответ. Повторите вопрос чуть позже."
GOODBYE_TEXT = "До свидания."

_STOP_PHRASES = frozenset(
    {
        "хватит",
        "хватит пожалуйста",
        "выход",
        "закончить",
        "стоп",
        "пока",
        "до свидания",
        "завершить",
        "алиса хватит",
    },
)
_CONTINUE_PHRASES = frozenset(
    {
        "дальше",
        "ну",
        "готово",
        "продолжай",
        "продолжить",
        "что там",
        "ну что",
    },
)
_SUPPORTED_REQUEST_TYPES = frozenset({"SimpleUtterance", "ButtonPressed"})


def fit_alice_text(text: str, limit: int = ALICE_TEXT_LIMIT) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[: limit - 1]
    pivot = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rfind("\n"))
    if pivot > limit // 2:
        return cut[: pivot + 1].rstrip()
    space = cut.rfind(" ")
    if space > limit // 2:
        return cut[:space].rstrip() + "…"
    return cut.rstrip() + "…"


def _normalize(text: str) -> str:
    return text.strip().lower().rstrip(".!?…")


class ReplyToUtteranceCommandHandler(
    cqrs.RequestHandler[ReplyToUtteranceCommand, ReplyToUtteranceResult],
):
    def __init__(self, language_model: LanguageModel, dialogs: DialogStore, settings: Settings) -> None:
        self._language_model = language_model
        self._dialogs = dialogs
        self._settings = settings

    async def handle(self, request: ReplyToUtteranceCommand) -> ReplyToUtteranceResult:
        if request.session_new:
            self._dialogs.reset(request.session_id)
        dialog = self._dialogs.get(request.session_id)
        async with dialog.lock:
            return await self._handle_locked(request, dialog)

    async def _handle_locked(self, request: ReplyToUtteranceCommand, dialog: Dialog) -> ReplyToUtteranceResult:
        if request.request_type not in _SUPPORTED_REQUEST_TYPES:
            return ReplyToUtteranceResult(text=UNSUPPORTED_TEXT)
        if request.dangerous:
            return ReplyToUtteranceResult(text=DANGEROUS_TEXT)

        utterance = request.utterance.strip()
        normalized = _normalize(utterance)
        if request.action == "stop" or normalized in _STOP_PHRASES:
            self._dialogs.reset(request.session_id)
            return ReplyToUtteranceResult(text=GOODBYE_TEXT, end_session=True)

        if request.session_new and not utterance:
            return ReplyToUtteranceResult(text=WELCOME_TEXT)

        if dialog.pending is not None:
            if not dialog.pending.done():
                return ReplyToUtteranceResult(text=WAIT_TEXT, suggest_continue=True)
            finished = self._take_pending(dialog)
            if finished is None:
                return ReplyToUtteranceResult(text=ERROR_TEXT)
            if request.action == "continue" or normalized in _CONTINUE_PHRASES or not utterance:
                return ReplyToUtteranceResult(text=finished)
            return ReplyToUtteranceResult(
                text=fit_alice_text(f"{finished} Это ответ на предыдущий вопрос. Повторите новый, если нужно."),
            )

        if not utterance or normalized in _CONTINUE_PHRASES or request.action == "continue":
            return ReplyToUtteranceResult(text=EMPTY_TEXT)

        dialog.messages.append({"role": "user", "content": utterance})
        self._dialogs.trim(dialog)
        messages: list[ChatMessage] = [
            {"role": "system", "content": self._settings.system_prompt},
            *dialog.messages,
        ]
        task = asyncio.create_task(self._complete(messages))
        dialog.pending = task
        try:
            text = await asyncio.wait_for(
                asyncio.shield(task),
                timeout=self._settings.alice_reply_budget_seconds,
            )
        except TimeoutError:
            return ReplyToUtteranceResult(text=WAIT_TEXT, suggest_continue=True)
        except Exception:
            dialog.pending = None
            logger.warning("language model failed for session %s", request.session_id, exc_info=True)
            return ReplyToUtteranceResult(text=ERROR_TEXT)
        dialog.pending = None
        if not text.strip():
            return ReplyToUtteranceResult(text=ERROR_TEXT)
        fitted = fit_alice_text(text)
        dialog.messages.append({"role": "assistant", "content": fitted})
        self._dialogs.trim(dialog)
        return ReplyToUtteranceResult(text=fitted)

    def _take_pending(self, dialog: Dialog) -> str | None:
        task = dialog.pending
        dialog.pending = None
        if task is None:
            return None
        try:
            text = task.result()
        except (LanguageModelError, asyncio.CancelledError, Exception):
            logger.warning("pending language model call failed", exc_info=True)
            return None
        if not text.strip():
            return None
        fitted = fit_alice_text(text)
        dialog.messages.append({"role": "assistant", "content": fitted})
        self._dialogs.trim(dialog)
        return fitted

    async def _complete(self, messages: list[ChatMessage]) -> str:
        return await self._language_model.complete(messages)
