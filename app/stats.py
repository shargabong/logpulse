"""Работа со статистикой в Redis.

Воркер после успешного разбора сообщения вызывает :func:`apply_event`.
Здесь же собрана функция чтения агрегатов для эндпоинта ``/stats``.
"""

from __future__ import annotations

from typing import Mapping

from .config import Settings
from .parser import (
    _validate_duration,
    _validate_rid,
    _validate_status,
    _validate_timestamp,
)


def normalize_event(fields: Mapping[str, str]) -> dict:
    """Привести поля сообщения из Redis Stream к типизированному событию."""
    timestamp = fields["timestamp"]
    _validate_timestamp(timestamp)
    return {
        "timestamp": timestamp,
        "level": fields["level"],
        "service": fields["service"],
        "ip": fields["ip"],
        "method": fields["method"],
        "path": fields["path"],
        "status": _validate_status(str(fields["status"])),
        "duration_ms": _validate_duration(str(fields["duration_ms"])),
        "rid": _validate_rid(fields["rid"]),
    }


async def apply_event(redis, event: dict, message_id: str, settings: Settings) -> bool:
    """Обновить статистику по одному событию.

    Возвращает ``False``, если сообщение уже было обработано ранее
    (идемпотентность при повторной доставке), иначе ``True``.
    """
    # SADD вернёт 0, если id сообщения уже встречался -> повторная доставка.
    is_new = await redis.sadd(settings.processed_key, message_id)
    if not is_new:
        return False

    pipe = redis.pipeline()
    pipe.hincrby(settings.level_key, event["level"], 1)
    pipe.hincrby(settings.service_key, event["service"], 1)
    pipe.hincrby(settings.status_key, str(event["status"]), 1)
    if event["duration_ms"] >= settings.slow_threshold_ms:
        # score = duration_ms, member = rid
        pipe.zadd(settings.slow_key, {event["rid"]: event["duration_ms"]})
    await pipe.execute()
    return True


def _as_int_hash(raw: Mapping[str, str]) -> dict[str, int]:
    return {str(key): int(value) for key, value in raw.items()}


async def read_stats(redis, settings: Settings, top_n: int = 5) -> dict:
    """Собрать агрегированную статистику из структур Redis."""
    by_level = _as_int_hash(await redis.hgetall(settings.level_key))
    by_service = _as_int_hash(await redis.hgetall(settings.service_key))
    by_status = _as_int_hash(await redis.hgetall(settings.status_key))
    slow = await redis.zrevrange(settings.slow_key, 0, top_n - 1, withscores=True)

    return {
        "total": sum(by_level.values()),
        "by_level": by_level,
        "by_service": by_service,
        "by_status": by_status,
        "top_slow": [
            {"rid": str(rid), "duration_ms": int(score)} for rid, score in slow
        ],
    }
