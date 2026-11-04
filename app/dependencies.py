"""Зависимости FastAPI.

Доступ к Redis вынесен в отдельную зависимость, чтобы её можно было
переопределить в тестах через ``app.dependency_overrides``.
"""

from __future__ import annotations

from fastapi import Request


def get_redis(request: Request):
    """Вернуть асинхронный клиент Redis, созданный в lifespan."""
    return request.app.state.redis
