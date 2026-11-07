"""Модели запросов и ответов (Pydantic)."""

from pydantic import BaseModel, Field, field_validator


class IngestRequest(BaseModel):
    """Тело запроса POST /ingest: от 1 до 100 строк, каждая 1-500 символов."""

    lines: list[str] = Field(..., min_length=1, max_length=100)

    @field_validator("lines")
    @classmethod
    def check_line_length(cls, value):
        for i, line in enumerate(value, start=1):
            if not 1 <= len(line) <= 500:
                raise ValueError(f"строка {i}: длина должна быть 1-500 символов")
        return value


class ParseErrorItem(BaseModel):
    """Ошибка разбора одной строки."""

    line: int
    reason: str


class IngestResponse(BaseModel):
    """Ответ POST /ingest."""

    accepted: int
    rejected: int
    errors: list[ParseErrorItem]


class SlowRequest(BaseModel):
    """Строка рейтинга медленных запросов."""

    rid: str
    duration_ms: int


class StatsResponse(BaseModel):
    """Ответ GET /stats."""

    total: int
    by_level: dict[str, int]
    by_service: dict[str, int]
    by_status: dict[str, int]
    top_slow: list[SlowRequest]


class EventItem(BaseModel):
    """Одно событие из Redis Stream."""

    id: str
    timestamp: str
    level: str
    service: str
    ip: str
    method: str
    path: str
    status: int
    duration_ms: int
    rid: str


class EventsResponse(BaseModel):
    """Ответ GET /events."""

    count: int
    events: list[EventItem]


class HealthResponse(BaseModel):
    """Ответ GET /health."""

    status: str
    redis: str


class ErrorBody(BaseModel):
    """Тело ошибки."""

    type: str
    message: str
    details: list[dict] | None = None


class ErrorResponse(BaseModel):
    """Единый формат ошибок."""

    error: ErrorBody
