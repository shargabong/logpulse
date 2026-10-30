"""Настройки приложения, читаемые из переменных окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from . import keys


@dataclass(frozen=True)
class Settings:
    """Конфигурация LogPulse.

    Значения по умолчанию рассчитаны на запуск через docker compose,
    где Redis доступен по DNS-имени ``redis``. Для локального запуска
    достаточно указать ``REDIS_URL=redis://localhost:6379/0``.
    """

    redis_url: str
    stream_key: str
    group_name: str
    slow_threshold_ms: int
    level_key: str
    service_key: str
    status_key: str
    slow_key: str
    processed_key: str
    redis_connect_timeout: float
    redis_socket_timeout: float


@lru_cache
def get_settings() -> Settings:
    """Вернуть настройки (кэшируются на время жизни процесса)."""
    return Settings(
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        stream_key=os.environ.get("LOGPULSE_STREAM", keys.STREAM_KEY),
        group_name=os.environ.get("LOGPULSE_GROUP", keys.GROUP_NAME),
        slow_threshold_ms=int(os.environ.get("SLOW_THRESHOLD_MS", "500")),
        level_key=keys.LEVEL_KEY,
        service_key=keys.SERVICE_KEY,
        status_key=keys.STATUS_KEY,
        slow_key=keys.SLOW_KEY,
        processed_key=keys.PROCESSED_KEY,
        # Таймауты, чтобы при недоступном Redis запросы падали быстро (503),
        # а не висели в ожидании ответа.
        redis_connect_timeout=float(os.environ.get("REDIS_CONNECT_TIMEOUT", "2")),
        redis_socket_timeout=float(os.environ.get("REDIS_SOCKET_TIMEOUT", "2")),
    )
