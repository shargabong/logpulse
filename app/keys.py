"""Ключи Redis, используемые приложением и воркером.

Все ключи вынесены в одно место, чтобы API и worker работали с одними
и теми же именами структур Redis.
"""

# Очередь событий (Redis Stream).
STREAM_KEY = "logpulse:events"

# Группа потребителей для воркера.
GROUP_NAME = "logpulse-workers"

# Счётчики (Redis Hash).
LEVEL_KEY = "logpulse:stats:level"
SERVICE_KEY = "logpulse:stats:service"
STATUS_KEY = "logpulse:stats:status"

# Рейтинг самых медленных запросов (Redis Sorted Set).
SLOW_KEY = "logpulse:slow"

# Множество уже обработанных сообщений — для идемпотентного обновления статистики.
PROCESSED_KEY = "logpulse:processed"
