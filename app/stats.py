"""Статистика в Redis: обновление счётчиков и чтение агрегатов."""

from .config import LEVEL_KEY, SERVICE_KEY, SLOW_KEY, SLOW_MS, STATUS_KEY


def to_event(fields):
    """Поля из Redis Stream (строки) превратить в событие с числами."""
    return {
        "timestamp": fields["timestamp"],
        "level": fields["level"],
        "service": fields["service"],
        "ip": fields["ip"],
        "method": fields["method"],
        "path": fields["path"],
        "status": int(fields["status"]),
        "duration_ms": int(fields["duration_ms"]),
        "rid": fields["rid"],
    }


def update_stats(r, event):
    """Обновить счётчики и рейтинг медленных запросов по одному событию."""
    pipe = r.pipeline()
    pipe.hincrby(LEVEL_KEY, event["level"], 1)
    pipe.hincrby(SERVICE_KEY, event["service"], 1)
    pipe.hincrby(STATUS_KEY, str(event["status"]), 1)
    if event["duration_ms"] >= SLOW_MS:
        # score = длительность, member = rid
        pipe.zadd(SLOW_KEY, {event["rid"]: event["duration_ms"]})
    pipe.execute()


def read_stats(r):
    """Собрать статистику из Redis для GET /stats."""
    by_level = {k: int(v) for k, v in r.hgetall(LEVEL_KEY).items()}
    by_service = {k: int(v) for k, v in r.hgetall(SERVICE_KEY).items()}
    by_status = {k: int(v) for k, v in r.hgetall(STATUS_KEY).items()}
    slow = r.zrevrange(SLOW_KEY, 0, 4, withscores=True)

    return {
        # total = сколько событий вообще обработал воркер (сумма счётчиков уровней)
        "total": sum(by_level.values()),
        "by_level": by_level,
        "by_service": by_service,
        "by_status": by_status,
        "top_slow": [
            {"rid": rid, "duration_ms": int(score)} for rid, score in slow
        ],
    }
