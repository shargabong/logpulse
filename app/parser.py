"""Разбор строк логов.

Формат строки:
    <UTC ISO-8601 Z> <LEVEL> <service> <IPv4> <METHOD> <path> <status> <N>ms rid=<8 hex>

Пример:
    2026-10-20T12:34:56Z INFO auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd34
"""

import ipaddress
import re
from datetime import datetime

# Основная маска с именованными группами. Разбираем строку целиком (fullmatch).
LOG_RE = re.compile(
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

# Отдельные маски для проверки полей (у каждой свой тест).
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$"
)
RID_RE = re.compile(r"^[0-9a-f]{8}$")
PATH_RE = re.compile(r"^/[A-Za-z0-9._~/{}\-]*$")
PROBLEM_RE = re.compile(r"\b(?:ERROR|WARN)\b")

LEVELS = ("INFO", "WARN", "ERROR")
SERVICES = ("auth", "orders", "payment")
METHODS = ("GET", "POST", "PUT", "DELETE")


class ParseError(ValueError):
    """Ошибка разбора строки: причина и (если известно) номер строки."""

    def __init__(self, reason, line=None):
        self.reason = reason
        self.line = line
        text = reason if line is None else f"строка {line}: {reason}"
        super().__init__(text)


def parse_line(line, line_no=None):
    """Разобрать одну строку. Вернёт словарь или бросит ParseError."""
    line = line.rstrip("\r\n")
    if not line.strip():
        raise ParseError("пустая строка", line_no)

    m = LOG_RE.fullmatch(line)
    if not m:
        raise ParseError("строка не соответствует формату лога", line_no)

    d = m.groupdict()

    # timestamp проверяем отдельной маской и datetime
    if not TS_RE.fullmatch(d["timestamp"]):
        raise ParseError("неверный timestamp: " + d["timestamp"], line_no)
    try:
        datetime.strptime(d["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise ParseError("timestamp не корректная дата: " + d["timestamp"], line_no)

    # IP проверяем через ipaddress, затем отдельной маской
    try:
        ipaddress.ip_address(d["ip"])
    except ValueError:
        raise ParseError("неверный IP: " + d["ip"], line_no)
    if not IPV4_RE.fullmatch(d["ip"]):
        raise ParseError("неверный IP: " + d["ip"], line_no)

    if d["level"] not in LEVELS:
        raise ParseError("недопустимый level: " + d["level"], line_no)
    if d["service"] not in SERVICES:
        raise ParseError("недопустимый service: " + d["service"], line_no)
    if d["method"] not in METHODS:
        raise ParseError("недопустимый method: " + d["method"], line_no)

    status = int(d["status"])
    if not 100 <= status <= 599:
        raise ParseError("код ответа вне 100-599: " + str(status), line_no)

    duration = int(d["duration_ms"])
    if not 0 <= duration <= 600000:
        raise ParseError("длительность вне 0-600000: " + str(duration), line_no)

    if not RID_RE.fullmatch(d["rid"]):
        raise ParseError("неверный rid: " + d["rid"], line_no)

    return {
        "timestamp": d["timestamp"],
        "level": d["level"],
        "service": d["service"],
        "ip": d["ip"],
        "method": d["method"],
        "path": d["path"],
        "status": status,
        "duration_ms": duration,
        "rid": d["rid"],
    }


def find_problem_lines(text):
    """Вернуть строки лога, где есть WARN или ERROR (поиск по маске)."""
    return [line for line in text.splitlines() if PROBLEM_RE.search(line)]
