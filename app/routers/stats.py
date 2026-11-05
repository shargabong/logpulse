"""Агрегированная статистика, накопленная воркером в Redis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from redis.exceptions import RedisError

from ..config import Settings, get_settings
from ..dependencies import get_redis
from ..models import ErrorResponse, StatsResponse
from ..stats import read_stats

router = APIRouter(tags=["stats"])


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Агрегированная статистика и ТОП медленных запросов",
    responses={503: {"model": ErrorResponse, "description": "Redis недоступен"}},
)
async def get_stats(redis=Depends(get_redis), settings: Settings = Depends(get_settings)):
    try:
        data = await read_stats(redis, settings)
    except (RedisError, OSError) as exc:
        raise HTTPException(status_code=503, detail="Redis недоступен") from exc
    return StatsResponse(**data)
