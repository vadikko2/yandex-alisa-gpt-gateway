from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, Request

from alice_gateway.presentation.protocol import alice_response, command_from_body
from alice_gateway.presentation.wiring.container import build_container, build_mediator
from alice_gateway.shared.settings import load_settings

logger = logging.getLogger(__name__)

_LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
_LOG_DATEFMT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    # python-cqrs sets this logger to DEBUG on import.
    logging.getLogger("cqrs").setLevel(logging.NOTSET)


def _token(value: object) -> str:
    text = value if isinstance(value, str) else ""
    text = " ".join(text.split())
    if not text:
        return "-"
    return text[:80]


def _utterance(text: str) -> str:
    collapsed = " ".join(text.split())
    if not collapsed:
        return "-"
    if len(collapsed) > 500:
        collapsed = collapsed[:500] + "…"
    escaped = collapsed.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _caller(body: dict[str, Any]) -> tuple[str, str]:
    session = body.get("session") if isinstance(body.get("session"), dict) else {}
    user = session.get("user") if isinstance(session.get("user"), dict) else {}
    application = session.get("application") if isinstance(session.get("application"), dict) else {}
    user_id = user.get("user_id") or session.get("user_id")
    return _token(user_id), _token(application.get("application_id"))


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return _token(first)
    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return _token(real_ip)
    if request.client is not None and request.client.host:
        return _token(request.client.host)
    return "-"


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
        started = time.perf_counter()
        body = await request.json()
        payload = body if isinstance(body, dict) else {}
        command = command_from_body(payload)
        result = await request.app.state.mediator.send(command)
        user_id, application_id = _caller(payload)
        logger.info(
            "POST /alice 200 ms=%s user=%s app=%s ip=%s session=%s text=%s",
            int((time.perf_counter() - started) * 1000),
            user_id,
            application_id,
            _client_ip(request),
            command.session_id,
            _utterance(command.utterance),
        )
        return alice_response(result)

    return app


def main() -> None:
    configure_logging()
    settings = load_settings()
    uvicorn.run(create_app(), host=settings.host, port=settings.port, access_log=False)
