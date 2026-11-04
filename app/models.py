"""Pydantic-модели запросов и ответов HTTP API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

LINE_MIN, LINE_MAX = 1, 500
LINES_MIN, LINES_MAX = 1, 100


class IngestRequest(BaseModel):
    """Запрос на приём пакета строк лога."""

    model_config = ConfigDict(extra="forbid")

    lines: list[str] = Field(
        ...,
        min_length=LINES_MIN,
        max_length=LINES_MAX,
        description="От 1 до 100 строк лога, каждая длиной 1-500 символов",
    )

    @field_validator("lines")
    @classmethod
    def _check_line_lengths(cls, value: list[str]) -> list[str]:
        for index, line in enumerate(value, start=1):
            if not LINE_MIN <= len(line) <= LINE_MAX:
                raise ValueError(
                    f"строка {index}: длина должна быть {LINE_MIN}-{LINE_MAX} символов"
                )
        return value


class ParseErrorItem(BaseModel):
    """Ошибка разбора одной строки с номером и причиной."""

    line: int = Field(..., description="Номер строки в пакете, начиная с 1")
    reason: str = Field(..., description="Причина отклонения")


class IngestResponse(BaseModel):
    """Результат приёма пакета строк."""

    accepted: int
    rejected: int
    errors: list[ParseErrorItem]


class SlowRequest(BaseModel):
    """Одна запись из рейтинга медленных запросов."""

    rid: str
    duration_ms: int


class StatsResponse(BaseModel):
    """Агрегированная статистика, собранная воркером в Redis."""

    total: int = Field(..., description="Всего обработанных worker событий")
    by_level: dict[str, int]
    by_service: dict[str, int]
    by_status: dict[str, int]
    top_slow: list[SlowRequest]


class EventItem(BaseModel):
    """Запись события из Redis Stream."""

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
    """Последние события из очереди."""

    count: int
    events: list[EventItem]


class HealthResponse(BaseModel):
    """Признак доступности приложения и Redis."""

    status: str
    redis: str


class ErrorBody(BaseModel):
    """Тело ошибки в едином формате."""

    type: str
    message: str
    details: list[dict] | None = None


class ErrorResponse(BaseModel):
    """Единый формат ошибок API."""

    error: ErrorBody
