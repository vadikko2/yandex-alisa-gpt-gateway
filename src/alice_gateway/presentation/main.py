from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, Request

from alice_gateway.presentation.protocol import alice_response, command_from_body
from alice_gateway.presentation.wiring.container import build_container, build_mediator
from alice_gateway.shared.settings import load_settings

logger = logging.getLogger(__name__)


class _SkipHealthAccessLog(logging.Filter):
    """Drop uvicorn access lines for GET /health so probes do not drown real traffic."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = build_container()
    app.state.mediator = build_mediator(container)
    app.state.language_model = container.language_model()
    yield
    close = getattr(app.state.language_model, "aclose", None)
    if close is not None:
        await close()


def create_app() -> FastAPI:
    app = FastAPI(title="Yandex Alice GPT gateway", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/alice")
    async def alice(request: Request) -> dict[str, Any]:
        body = await request.json()
        command = command_from_body(body if isinstance(body, dict) else {})
        result = await request.app.state.mediator.send(command)
        logger.info(
            "alice session=%s new=%s type=%s chars=%s",
            command.session_id,
            command.session_new,
            command.request_type,
            len(command.utterance),
        )
        return alice_response(result)

    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("uvicorn.access").addFilter(_SkipHealthAccessLog())
    settings = load_settings()
    uvicorn.run(create_app(), host=settings.host, port=settings.port)
