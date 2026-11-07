"""Воркер LogPulse.

Читает события из Redis Stream (XREADGROUP), обновляет статистику и
подтверждает обработку (XACK). Если Redis недоступен, не падает, а ждёт
и пробует снова.

Запуск: python worker.py
"""

import os
import time

import redis

from app.config import GROUP_NAME, REDIS_URL, STREAM_KEY
from app.stats import to_event, update_stats

BATCH = 10


def consume_once(r, name):
    """Забрать пачку сообщений и обработать их."""
    response = r.xreadgroup(
        GROUP_NAME, name, {STREAM_KEY: ">"}, count=BATCH, block=2000
    )
    if not response:
        return
    for _stream, messages in response:
        for msg_id, fields in messages:
            try:
                event = to_event(fields)
                update_stats(r, event)
                print("обработано", msg_id, event["level"], event["rid"])
            except (KeyError, ValueError):
                print("битое сообщение, пропускаю", msg_id)
            r.xack(STREAM_KEY, GROUP_NAME, msg_id)


def main():
    r = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    name = os.environ.get("WORKER_NAME", "worker-1")

    try:
        r.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
    except redis.ResponseError:
        pass  # группа уже создана раньше

    print("воркер запущен:", name)

    while True:
        try:
            consume_once(r, name)
        except redis.RedisError as exc:
            print("нет связи с Redis:", exc, "- повтор через 2 сек")
            time.sleep(2)


if __name__ == "__main__":
    main()
