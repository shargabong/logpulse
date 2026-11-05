"""Тесты накопления статистики и идемпотентности обновления."""

from __future__ import annotations

import asyncio

from app.config import get_settings
from app.stats import apply_event, read_stats


def run(coro):
    return asyncio.run(coro)


def make_event(level="INFO", service="auth", status=200, duration_ms=100, rid="a0000001"):
    return {
        "timestamp": "2026-10-20T12:00:00Z",
        "level": level,
        "service": service,
        "ip": "192.0.2.10",
        "method": "GET",
        "path": "/api/resource",
        "status": status,
        "duration_ms": duration_ms,
        "rid": rid,
    }


def test_counters_accumulate(fake_redis):
    async def scenario():
        settings = get_settings()
        await apply_event(fake_redis, make_event(level="INFO"), "1-0", settings)
        await apply_event(fake_redis, make_event(level="INFO"), "2-0", settings)
        await apply_event(fake_redis, make_event(level="ERROR", status=500), "3-0", settings)
        data = await read_stats(fake_redis, settings)
        assert data["total"] == 3
        assert data["by_level"]["INFO"] == 2
        assert data["by_level"]["ERROR"] == 1
        assert data["by_status"]["500"] == 1

    run(scenario())


def test_counts_by_service(fake_redis):
    async def scenario():
        settings = get_settings()
        await apply_event(fake_redis, make_event(service="auth"), "1-0", settings)
        await apply_event(fake_redis, make_event(service="orders"), "2-0", settings)
        await apply_event(fake_redis, make_event(service="orders"), "3-0", settings)
        data = await read_stats(fake_redis, settings)
        assert data["by_service"]["orders"] == 2
        assert data["by_service"]["auth"] == 1

    run(scenario())


def test_top_slow_sorted(fake_redis):
    async def scenario():
        settings = get_settings()
        await apply_event(fake_redis, make_event(duration_ms=700, rid="a0000001"), "1-0", settings)
        await apply_event(fake_redis, make_event(duration_ms=1200, rid="b0000002"), "2-0", settings)
        await apply_event(fake_redis, make_event(duration_ms=900, rid="c0000003"), "3-0", settings)
        data = await read_stats(fake_redis, settings)
        durations = [item["duration_ms"] for item in data["top_slow"]]
        assert durations == [1200, 900, 700]
        assert data["top_slow"][0]["rid"] == "b0000002"

    run(scenario())


def test_slow_threshold(fake_redis):
    async def scenario():
        settings = get_settings()
        # Ниже порога (500 мс) в рейтинг не попадает.
        await apply_event(fake_redis, make_event(duration_ms=499, rid="a0000001"), "1-0", settings)
        data = await read_stats(fake_redis, settings)
        assert data["top_slow"] == []

    run(scenario())


def test_idempotent_redelivery(fake_redis):
    async def scenario():
        settings = get_settings()
        first = await apply_event(fake_redis, make_event(), "1-0", settings)
        second = await apply_event(fake_redis, make_event(), "1-0", settings)
        data = await read_stats(fake_redis, settings)
        assert first is True
        assert second is False
        # Повторная доставка не удвоила счётчики.
        assert data["total"] == 1

    run(scenario())
