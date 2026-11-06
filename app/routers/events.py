"""Последние записи очереди Redis Stream."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.exceptions import RedisError

from ..config import Settings, get_settings
from ..dependencies import get_redis
from ..models import ErrorResponse, EventItem, EventsResponse
from ..stats import normalize_event

router = APIRouter(tags=["events"])


@router.get(
    "/events",
    response_model=EventsResponse,
    summary="Последние записи Redis Stream",
    responses={503: {"model": ErrorResponse, "description": "Redis недоступен"}},
)
async def list_events(
    limit: int = Query(10, ge=1, le=50, description="Сколько записей вернуть (1-50)"),
    redis=Depends(get_redis),
    settings: Settings = Depends(get_settings),
):
    try:
        rows = await redis.xrevrange(settings.stream_key, max="+", min="-", count=limit)
    except (RedisError, OSError) as exc:
        raise HTTPException(status_code=503, detail="Redis недоступен") from exc

    events: list[EventItem] = []
    for message_id, fields in rows:
        try:
            event = normalize_event(fields)
        except (KeyError, ValueError):
            # Битые записи в поток не попадают, но на всякий случай пропускаем.
            continue
        events.append(EventItem(id=str(message_id), **event))

    return EventsResponse(count=len(events), events=events)
