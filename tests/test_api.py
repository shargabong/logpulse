"""Тесты HTTP API (FastAPI TestClient + fakeredis)."""

import redis
from fastapi.testclient import TestClient

from app.config import STREAM_KEY
from app.main import app
from app.redis_client import get_redis
from app.stats import to_event, update_stats

VALID_1 = (
    "2026-10-20T12:34:56Z INFO auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd34"
)
VALID_2 = (
    "2026-10-20T12:34:58Z ERROR orders 198.51.100.8 GET /api/orders 503 742ms rid=ee44cc22"
)
VALID_3 = (
    "2026-10-20T12:35:01Z WARN payment 203.0.113.7 POST /api/pay 429 301ms rid=ff44aa33"
)
BROKEN_STATUS = (
    "2026-10-20T12:35:04Z ERROR orders 198.51.100.8 GET /api/orders 999 100ms rid=aa11bb22"
)
BROKEN_IP = (
    "2026-10-20T12:35:07Z INFO auth 999.1.1.1 POST /api/login 200 43ms rid=cc33dd44"
)


class DownRedis:
    """Заглушка недоступного Redis."""

    def ping(self):
        raise redis.ConnectionError("redis down")


def process_stream(r):
    """Имитация воркера: прочитать поток и обновить статистику."""
    for _mid, fields in r.xrange(STREAM_KEY, "-", "+"):
        update_stats(r, to_event(fields))


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "redis": "ok"}


def test_health_without_redis():
    app.dependency_overrides[get_redis] = lambda: DownRedis()
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/health")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["error"]["type"] == "service_unavailable"


def test_ingest_mixed_packet(client):
    response = client.post(
        "/ingest",
        json={"lines": [VALID_1, VALID_2, VALID_3, BROKEN_STATUS, BROKEN_IP]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 3
    assert data["rejected"] == 2
    assert {e["line"] for e in data["errors"]} == {4, 5}


def test_ingest_wrong_schema(client):
    response = client.post("/ingest", json={"foo": "bar"})
    assert response.status_code == 422
    assert response.json()["error"]["type"] == "validation_error"


def test_ingest_empty_lines(client):
    assert client.post("/ingest", json={"lines": []}).status_code == 422


def test_ingest_too_many_lines(client):
    assert client.post("/ingest", json={"lines": ["x"] * 101}).status_code == 422


def test_ingest_line_too_long(client):
    assert client.post("/ingest", json={"lines": ["x" * 501]}).status_code == 422


def test_stats_after_worker(client, fake_redis):
    client.post("/ingest", json={"lines": [VALID_1, VALID_2, VALID_3]})
    process_stream(fake_redis)

    data = client.get("/stats").json()
    assert data["total"] == 3
    assert data["by_level"]["INFO"] == 1
    assert data["by_status"]["503"] == 1
    # валидная строка 2 длится 742 мс -> в рейтинге медленных
    assert data["top_slow"][0]["rid"] == "ee44cc22"


def test_events_limit(client):
    client.post("/ingest", json={"lines": [VALID_1, VALID_2]})
    data = client.get("/events?limit=1").json()
    assert data["count"] == 1
    assert data["events"][0]["rid"] == "ee44cc22"


def test_events_invalid_limit(client):
    assert client.get("/events?limit=0").status_code == 422
    assert client.get("/events?limit=51").status_code == 422


def test_unknown_route_error_format(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["type"] == "not_found"
