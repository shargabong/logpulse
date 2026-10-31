"""Парсер строк сервисного лога.

Формат строки строго фиксирован:

    <UTC ISO-8601 с Z> <LEVEL> <service> <IPv4> <METHOD> <path> <status> <N>ms rid=<8 hex>

Пример:

    2026-10-20T12:34:56Z INFO auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd34

Основной разбор делает одна регулярная маска с именованными группами и
полным сопоставлением строки (``re.fullmatch``). Дополнительно применяются
отдельные выражения для проверки отдельных полей (см. ``_FIELD_RE``).

После сопоставления поля проверяются уже типами Python:
timestamp через ``datetime``, IP через ``ipaddress``, а числовые поля — по
допустимым диапазонам.
"""

from __future__ import annotations

import ipaddress
import re
from datetime import datetime

# --- Основная маска -------------------------------------------------------
#
# Именованные группы: timestamp, level, service, ip, method, path,
# status, duration_ms, rid. Полное сопоставление строки.
LOG_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+"
    r"(?P<level>INFO|WARN|ERROR)\s+"
    r"(?P<service>auth|orders|payment)\s+"
    r"(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s+"
    r"(?P<method>GET|POST|PUT|DELETE)\s+"
    r"(?P<path>/\S+)\s+"
    r"(?P<status>\d{3})\s+"
    r"(?P<duration_ms>\d+)ms\s+"
    r"rid=(?P<rid>[0-9a-f]{8})"
)

# --- Отдельные выражения для проверки/поиска полей ------------------------
#
# Каждое выражение снабжено отдельным тестом (tests/test_parser.py).
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$"
)
RID_RE = re.compile(r"^[0-9a-f]{8}$")
PATH_RE = re.compile(r"^/[A-Za-z0-9._~/{}\-]*$")
# Поиск потенциально проблемных строк в логе.
PROBLEM_RE = re.compile(r"\b(?:ERROR|WARN)\b")

_FIELD_RE = {
    "timestamp": TS_RE,
    "ip": IPV4_RE,
    "rid": RID_RE,
    "path": PATH_RE,
}

ALLOWED_LEVELS = frozenset({"INFO", "WARN", "ERROR"})
ALLOWED_SERVICES = frozenset({"auth", "orders", "payment"})
ALLOWED_METHODS = frozenset({"GET", "POST", "PUT", "DELETE"})

STATUS_MIN, STATUS_MAX = 100, 599
DURATION_MIN, DURATION_MAX = 0, 600_000

_TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class ParseError(ValueError):
    """Ошибка разбора строки лога с понятной причиной."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def check_field(field: str, value: str) -> bool:
    """Проверить одно поле отдельным регулярным выражением."""
    pattern = _FIELD_RE.get(field)
    if pattern is None:
        raise KeyError(f"нет отдельного выражения для поля {field!r}")
    return pattern.fullmatch(value) is not None


def find_problem_lines(text: str) -> list[str]:
    """Вернуть строки, содержащие WARN/ERROR (поиск паттерна в логе)."""
    return [line for line in text.splitlines() if PROBLEM_RE.search(line)]


def parse_line(line: str, line_no: int | None = None) -> dict:
    """Разобрать одну строку лога.

    Возвращает нормализованный словарь с типизированными значениями.
    При любой проблеме поднимает :class:`ParseError` с причиной.
    """
    raw = line.rstrip("\r\n")
    if not raw.strip():
        raise ParseError("пустая строка")

    match = LOG_PATTERN.fullmatch(raw)
    if match is None:
        raise ParseError("строка не соответствует формату лога")

    data = match.groupdict()

    _validate_timestamp(data["timestamp"])
    _validate_ip(data["ip"])
    level = _validate_choice("level", data["level"], ALLOWED_LEVELS)
    service = _validate_choice("service", data["service"], ALLOWED_SERVICES)
    method = _validate_choice("method", data["method"], ALLOWED_METHODS)
    status = _validate_status(data["status"])
    duration_ms = _validate_duration(data["duration_ms"])
    rid = _validate_rid(data["rid"])

    return {
        "timestamp": data["timestamp"],
        "level": level,
        "service": service,
        "ip": data["ip"],
        "method": method,
        "path": data["path"],
        "status": status,
        "duration_ms": duration_ms,
        "rid": rid,
    }


def _validate_timestamp(value: str) -> None:
    if not TS_RE.fullmatch(value):
        raise ParseError(f"неверный timestamp: {value!r}")
    try:
        datetime.strptime(value, _TS_FORMAT)
    except ValueError:
        raise ParseError(f"timestamp не является корректной датой: {value!r}")


def _validate_ip(value: str) -> None:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        raise ParseError(f"неверный IP-адрес: {value!r}")
    if ip.version != 4:
        raise ParseError(f"IP-адрес не является IPv4: {value!r}")


def _validate_choice(field: str, value: str, allowed: frozenset) -> str:
    if value not in allowed:
        raise ParseError(f"недопустимое значение {field}: {value!r}")
    return value


def _validate_status(value: str) -> int:
    status = int(value)
    if not STATUS_MIN <= status <= STATUS_MAX:
        raise ParseError(
            f"код ответа вне диапазона {STATUS_MIN}-{STATUS_MAX}: {status}"
        )
    return status


def _validate_duration(value: str) -> int:
    duration = int(value)
    if not DURATION_MIN <= duration <= DURATION_MAX:
        raise ParseError(
            f"длительность вне диапазона {DURATION_MIN}-{DURATION_MAX} мс: {duration}"
        )
    return duration


def _validate_rid(value: str) -> str:
    if not RID_RE.fullmatch(value):
        raise ParseError(f"неверный rid (нужно 8 hex-символов): {value!r}")
    return value
