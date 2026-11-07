"""Клиент Redis и зависимость для FastAPI."""

import redis

from .config import REDIS_URL

# Один общий клиент на всё приложение.
# Таймауты нужны, чтобы при недоступном Redis запросы падали быстро (503),
# а не висели.
client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def get_redis():
    """Зависимость FastAPI. В тестах подменяется через dependency_overrides."""
    return client
