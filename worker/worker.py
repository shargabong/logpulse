"""Фоновый обработчик событий LogPulse.

Читает события из Redis Stream через XREADGROUP (consumer group
``logpulse-workers``), обновляет статистику в Redis и подтверждает
обработку командой XACK. Ошибки связи с Redis не приводят к аварийному
завершению: воркер ждёт и повторяет попытку с нарастающей паузой.

Запуск::

    python -m worker.worker
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal

import redis.asyncio as aioredis
from redis.exceptions import RedisError, ResponseError

from app.config import Settings, get_settings
from app.stats import apply_event, normalize_event

logger = logging.getLogger("logpulse.worker")

BATCH_SIZE = 10
BLOCK_MS = 5000
MAX_BACKOFF = 30.0


class Worker:
    """Читает поток событий и наполняет статистику Redis."""

    def __init__(self, redis, settings: Settings, consumer: str) -> None:
        self.redis = redis
        self.settings = settings
        self.consumer = consumer

    async def ensure_group(self) -> None:
        """Создать группу потребителей, если её ещё нет."""
        try:
            await self.redis.xgroup_create(
                self.settings.stream_key,
                self.settings.group_name,
                id="0",
                mkstream=True,
            )
            logger.info("Создана группа потребителей %s", self.settings.group_name)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def run(self, stop: asyncio.Event) -> None:
        """Основной цикл с переподключением при сбоях Redis."""
        backoff = 1.0
        while not stop.is_set():
            try:
                await self.ensure_group()
                backoff = 1.0
                await self._consume(stop)
            except (RedisError, OSError) as exc:
                logger.warning(
                    "Связь с Redis потеряна (%s). Повтор через %.0f с.", exc, backoff
                )
                await _sleep_or_stop(stop, backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)

    async def _consume(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            response = await self.redis.xreadgroup(
                self.settings.group_name,
                self.consumer,
                {self.settings.stream_key: ">"},
                count=BATCH_SIZE,
                block=BLOCK_MS,
            )
            if not response:
                continue
            for _stream, messages in response:
                for message_id, fields in messages:
                    await self._handle(message_id, fields)

    async def _handle(self, message_id: str, fields: dict) -> None:
        try:
            event = normalize_event(fields)
        except (KeyError, ValueError) as exc:
            logger.warning("Битое сообщение %s пропущено: %s", message_id, exc)
            await self._ack(message_id)
            return

        updated = await apply_event(self.redis, event, message_id, self.settings)
        await self._ack(message_id)
        if updated:
            logger.info(
                "Обработано %s %s %s rid=%s",
                event["level"],
                event["service"],
                event["status"],
                event["rid"],
            )

    async def _ack(self, message_id: str) -> None:
        await self.redis.xack(
            self.settings.stream_key, self.settings.group_name, message_id
        )


async def _sleep_or_stop(stop: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except asyncio.TimeoutError:
        pass


def _install_signal_handlers(stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except (NotImplementedError, RuntimeError, ValueError):
            # Windows не поддерживает add_signal_handler для этих сигналов.
            signal.signal(sig, lambda *_: stop.set())


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = get_settings()
    consumer = os.environ.get("WORKER_NAME", f"worker-{os.getpid()}")
    redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=settings.redis_connect_timeout,
        socket_timeout=settings.redis_socket_timeout,
    )
    worker = Worker(redis, settings, consumer)
    stop = asyncio.Event()
    _install_signal_handlers(stop)

    logger.info("Воркер %s запущен (Redis: %s)", consumer, settings.redis_url)
    try:
        await worker.run(stop)
    finally:
        await redis.aclose()
        logger.info("Воркер остановлен")


if __name__ == "__main__":
    asyncio.run(main())
