"""HTTP-маршруты LogPulse (FastAPI APIRouter)."""

import redis
from fastapi import APIRouter, Depends, HTTPException, Query

from .config import STREAM_KEY
from .models import (
    ErrorResponse,
    EventsResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    StatsResponse,
)
from .parser import ParseError, parse_line
from .redis_client import get_redis
from .stats import read_stats, to_event

router = APIRouter()

redis_down = {503: {"model": ErrorResponse, "description": "Redis недоступен"}}


@router.get("/health", response_model=HealthResponse, responses=redis_down)
def health(r=Depends(get_redis)):
    """Признак доступности приложения и Redis."""
    try:
        r.ping()
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Redis недоступен")
    return {"status": "ok", "redis": "ok"}


@router.post("/ingest", response_model=IngestResponse, responses=redis_down)
def ingest(data: IngestRequest, r=Depends(get_redis)):
    """Принять пакет строк: валидные уходят в Redis Stream, ошибочные в errors."""
    accepted = 0
    errors = []
    for i, line in enumerate(data.lines, start=1):
        try:
            event = parse_line(line)
        except ParseError as exc:
            errors.append({"line": i, "reason": str(exc)})
            continue
        try:
            r.xadd(STREAM_KEY, event)
        except redis.RedisError:
            raise HTTPException(status_code=503, detail="Redis недоступен")
        accepted += 1
    return {"accepted": accepted, "rejected": len(errors), "errors": errors}


@router.get("/stats", response_model=StatsResponse, responses=redis_down)
def stats(r=Depends(get_redis)):
    """Агрегированная статистика и ТОП медленных запросов."""
    try:
        return read_stats(r)
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Redis недоступен")


@router.get("/events", response_model=EventsResponse, responses=redis_down)
def events(limit: int = Query(10, ge=1, le=50), r=Depends(get_redis)):
    """Последние записи Redis Stream (limit от 1 до 50)."""
    try:
        rows = r.xrevrange(STREAM_KEY, "+", "-", count=limit)
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Redis недоступен")
    items = [{"id": mid, **to_event(fields)} for mid, fields in rows]
    return {"count": len(items), "events": items}
