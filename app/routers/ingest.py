"""Приём строк лога, разбор и публикация валидных событий в Redis Stream."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from redis.exceptions import RedisError

from ..config import Settings, get_settings
from ..dependencies import get_redis
from ..models import ErrorResponse, IngestRequest, IngestResponse, ParseErrorItem
from ..parser import ParseError, parse_line

router = APIRouter(tags=["ingest"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Принять пакет строк лога",
    responses={
        422: {"model": ErrorResponse, "description": "Ошибка структуры запроса"},
        503: {"model": ErrorResponse, "description": "Redis недоступен"},
    },
)
async def ingest(
    payload: IngestRequest,
    redis=Depends(get_redis),
    settings: Settings = Depends(get_settings),
):
    try:
        await redis.ping()
    except (RedisError, OSError) as exc:
        raise HTTPException(status_code=503, detail="Redis недоступен") from exc

    accepted = 0
    errors: list[ParseErrorItem] = []

    for index, line in enumerate(payload.lines, start=1):
        try:
            event = parse_line(line, index)
        except ParseError as exc:
            errors.append(ParseErrorItem(line=index, reason=exc.reason))
            continue

        try:
            await redis.xadd(settings.stream_key, event)
        except (RedisError, OSError) as exc:
            raise HTTPException(status_code=503, detail="Redis недоступен") from exc
        accepted += 1

    return IngestResponse(accepted=accepted, rejected=len(errors), errors=errors)
