"""Проверка доступности приложения и Redis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from redis.exceptions import RedisError

from ..config import Settings, get_settings
from ..dependencies import get_redis
from ..models import ErrorResponse, HealthResponse

router = APIRouter(tags=["service"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Доступность приложения и Redis",
    responses={503: {"model": ErrorResponse, "description": "Redis недоступен"}},
)
async def health(redis=Depends(get_redis), settings: Settings = Depends(get_settings)):
    try:
        await redis.ping()
    except (RedisError, OSError) as exc:
        raise HTTPException(status_code=503, detail="Redis недоступен") from exc
    return HealthResponse(status="ok", redis="ok")
