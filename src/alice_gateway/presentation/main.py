from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, Request

from alice_gateway.presentation.protocol import alice_response, command_from_body
from alice_gateway.presentation.wiring.container import build_container, build_mediator
from alice_gateway.service.models.commands.reply import ReplyToUtteranceResult
from alice_gateway.shared.settings import load_settings

logger = logging.getLogger(__name__)

_LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
_LOG_DATEFMT = "%Y-%m-%dT%H:%M:%S%z"
_CIDR = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}/\d{1,3}|(?:[0-9a-fA-F]{1,4}:){2,}[0-9a-fA-F:]*/\d{1,3}")
# https://yandex.ru/ips — used until the page is fetched, and if that fetch comes back empty.
_PUBLISHED_YANDEX_NETWORKS = (
    "5.45.192.0/18",
    "5.255.192.0/18",
    "37.9.64.0/18",
    "37.140.128.0/18",
    "77.88.0.0/18",
    "84.252.160.0/19",
    "87.250.224.0/19",
    "90.156.176.0/20",
    "92.255.112.0/20",
    "93.158.128.0/18",
    "95.108.128.0/17",
    "141.8.128.0/18",
    "178.154.128.0/18",
    "185.32.187.0/24",
    "213.180.192.0/19",
    "2a02:6b8::/29",
)
yandex_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network(network) for network in _PUBLISHED_YANDEX_NETWORKS
]


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


async def _refresh_yandex_ips() -> None:
    while True:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                page = (
                    await client.get("https://yandex.ru/ips", headers={"user-agent": "Mozilla/5.0"})
                ).text
            found = list(dict.fromkeys(ipaddress.ip_network(token) for token in _CIDR.findall(page)))
            if found:
                yandex_networks[:] = found
                logger.info("yandex ips cached networks=%s", len(found))
            else:
                logger.warning("yandex ips page has no networks")
        except Exception:
            logger.warning("yandex ips refresh failed", exc_info=True)
        await asyncio.sleep(86400 if yandex_networks else 60)


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


def _from_yandex(request: Request) -> bool:
    try:
        address = ipaddress.ip_address(_client_ip(request))
    except ValueError:
        return False
    return any(address in network for network in yandex_networks)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = build_container()
    app.state.mediator = build_mediator(container)
    app.state.language_model = container.language_model()
    refresh_task = asyncio.create_task(_refresh_yandex_ips())
    try:
        yield
    finally:
        refresh_task.cancel()
        with suppress(asyncio.CancelledError):
            await refresh_task
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
        if not _from_yandex(request):
            logger.info("POST /alice 200 ip=%s denied", _client_ip(request))
            return alice_response(
                ReplyToUtteranceResult(
                    text="Запрос должен быть с адресов Яндекса.",
                    end_session=True,
                ),
            )
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
