"""Точка входа FastAPI-приложения LogPulse."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .config import get_settings
from .routers import events, health, ingest, stats

logger = logging.getLogger("logpulse.api")

_STATUS_TYPES = {
    404: "not_found",
    422: "validation_error",
    503: "service_unavailable",
}


def _error_payload(error_type: str, message: str, details=None) -> dict:
    body = {"type": error_type, "message": message}
    if details is not None:
        body["details"] = details
    return {"error": body}


def _clean_validation_errors(errors: list[dict]) -> list[dict]:
    """Оставить в ошибках только JSON-совместимые поля."""
    cleaned = []
    for item in errors:
        cleaned.append(
            {
                "loc": [str(part) for part in item.get("loc", [])],
                "msg": str(item.get("msg", "")),
                "type": str(item.get("type", "")),
            }
        )
    return cleaned


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Создать и закрыть клиент Redis на время жизни приложения."""
    settings = get_settings()
    app.state.redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=settings.redis_connect_timeout,
        socket_timeout=settings.redis_socket_timeout,
    )
    logger.info("LogPulse API запущен, Redis: %s", settings.redis_url.split("@")[-1])
    try:
        yield
    finally:
        await app.state.redis.aclose()


app = FastAPI(
    title="LogPulse",
    description="Приём и разбор сервисных логов, статистика в Redis.",
    version=__version__,
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(stats.router)
app.include_router(events.router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    error_type = _STATUS_TYPES.get(exc.status_code, "http_error")
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(error_type, str(exc.detail)),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=_error_payload(
            "validation_error",
            "ошибка структуры запроса",
            _clean_validation_errors(exc.errors()),
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Необработанная ошибка: %s", exc)
    # Наружу не отдаём трассировку и детали.
    return JSONResponse(
        status_code=500,
        content=_error_payload("internal_error", "внутренняя ошибка сервера"),
    )
