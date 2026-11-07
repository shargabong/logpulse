"""Общие фикстуры: подменяем Redis на fakeredis, данные проекта не трогаем."""

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.redis_client import get_redis


@pytest.fixture
def fake_redis():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def client(fake_redis):
    app.dependency_overrides[get_redis] = lambda: fake_redis
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
