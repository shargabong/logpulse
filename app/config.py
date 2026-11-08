"""Настройки и ключи Redis. Значения читаются из переменных окружения."""

import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

STREAM_KEY = os.environ.get("LOGPULSE_STREAM", "logpulse:events")
GROUP_NAME = os.environ.get("LOGPULSE_GROUP", "logpulse-workers")

SLOW_MS = int(os.environ.get("SLOW_THRESHOLD_MS", "500"))

# Ключи со статистикой
LEVEL_KEY = "logpulse:stats:level"
SERVICE_KEY = "logpulse:stats:service"
STATUS_KEY = "logpulse:stats:status"
SLOW_KEY = "logpulse:slow"
