"""Общие фикстуры для тестов API."""

from __future__ import annotations

import pytest
from fakeredis import aioredis as fakeredis_aioredis
from fastapi.testclient import TestClient

from app.dependencies import get_redis
from app.main import app


@pytest.fixture
def fake_redis():
    """Изолированный Redis на время теста (реальные данные не трогаем)."""
    return fakeredis_aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def client(fake_redis):
    """TestClient с подменённой зависимостью Redis."""
    app.dependency_overrides[get_redis] = lambda: fake_redis
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
