"""Тесты накопления статистики в Redis."""

from app.stats import read_stats, to_event, update_stats


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


def test_to_event_makes_numbers():
    fields = {
        "timestamp": "2026-10-20T12:00:00Z",
        "level": "INFO",
        "service": "auth",
        "ip": "192.0.2.10",
        "method": "GET",
        "path": "/api/x",
        "status": "200",
        "duration_ms": "43",
        "rid": "ab12cd34",
    }
    e = to_event(fields)
    assert e["status"] == 200
    assert e["duration_ms"] == 43


def test_counters_accumulate(fake_redis):
    update_stats(fake_redis, make_event(level="INFO"))
    update_stats(fake_redis, make_event(level="INFO"))
    update_stats(fake_redis, make_event(level="ERROR", status=500))
    data = read_stats(fake_redis)
    assert data["total"] == 3
    assert data["by_level"]["INFO"] == 2
    assert data["by_level"]["ERROR"] == 1
    assert data["by_status"]["500"] == 1


def test_counts_by_service(fake_redis):
    update_stats(fake_redis, make_event(service="auth"))
    update_stats(fake_redis, make_event(service="orders"))
    update_stats(fake_redis, make_event(service="orders"))
    data = read_stats(fake_redis)
    assert data["by_service"]["orders"] == 2
    assert data["by_service"]["auth"] == 1


def test_top_slow_sorted(fake_redis):
    update_stats(fake_redis, make_event(duration_ms=700, rid="a0000001"))
    update_stats(fake_redis, make_event(duration_ms=1200, rid="b0000002"))
    update_stats(fake_redis, make_event(duration_ms=900, rid="c0000003"))
    data = read_stats(fake_redis)
    assert [x["duration_ms"] for x in data["top_slow"]] == [1200, 900, 700]
    assert data["top_slow"][0]["rid"] == "b0000002"


def test_slow_threshold(fake_redis):
    update_stats(fake_redis, make_event(duration_ms=499, rid="a0000001"))
    assert read_stats(fake_redis)["top_slow"] == []
