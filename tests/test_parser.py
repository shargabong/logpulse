"""Тесты парсера и регулярных выражений."""

from __future__ import annotations

import pytest

from app.parser import (
    IPV4_RE,
    PATH_RE,
    RID_RE,
    TS_RE,
    ParseError,
    check_field,
    find_problem_lines,
    parse_line,
)

VALID_INFO = (
    "2026-10-20T12:34:56Z INFO auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd34"
)
VALID_ERROR = (
    "2026-10-20T12:34:58Z ERROR orders 198.51.100.8 GET /api/orders 503 742ms rid=ee44cc22"
)
VALID_WARN = (
    "2026-10-20T12:35:01Z WARN payment 203.0.113.7 POST /api/pay 429 301ms rid=ff44aa33"
)


def test_parse_valid_info():
    event = parse_line(VALID_INFO)
    assert event["level"] == "INFO"
    assert event["service"] == "auth"
    assert event["method"] == "POST"
    assert event["path"] == "/api/login"
    assert event["status"] == 200
    assert event["duration_ms"] == 43
    assert event["rid"] == "ab12cd34"


def test_parse_valid_error():
    event = parse_line(VALID_ERROR)
    assert event["level"] == "ERROR"
    assert event["service"] == "orders"
    assert event["status"] == 503
    assert event["duration_ms"] == 742


def test_parse_valid_warn():
    event = parse_line(VALID_WARN)
    assert event["level"] == "WARN"
    assert event["ip"] == "203.0.113.7"


def test_normalized_types():
    event = parse_line(VALID_INFO)
    # Числовые поля возвращаются как int, а не как str.
    assert isinstance(event["status"], int)
    assert isinstance(event["duration_ms"], int)


def test_broken_timestamp():
    line = "2026-13-45T99:99:99Z INFO auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd34"
    with pytest.raises(ParseError) as exc:
        parse_line(line)
    assert "timestamp" in exc.value.reason


def test_invalid_ipv4():
    line = "2026-10-20T12:34:56Z INFO auth 999.1.1.1 POST /api/login 200 43ms rid=ab12cd34"
    with pytest.raises(ParseError) as exc:
        parse_line(line)
    assert "IP" in exc.value.reason


@pytest.mark.parametrize("level", ["DEBUG", "TRACE", "FATAL"])
def test_unsupported_level(level):
    line = f"2026-10-20T12:34:56Z {level} auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd34"
    with pytest.raises(ParseError):
        parse_line(line)


def test_invalid_status():
    line = "2026-10-20T12:34:56Z ERROR orders 198.51.100.8 GET /api/orders 999 742ms rid=ee44cc22"
    with pytest.raises(ParseError) as exc:
        parse_line(line)
    assert "код ответа" in exc.value.reason


def test_duration_out_of_range():
    line = "2026-10-20T12:34:56Z INFO auth 192.0.2.10 POST /api/login 200 700000ms rid=ab12cd34"
    with pytest.raises(ParseError) as exc:
        parse_line(line)
    assert "длительность" in exc.value.reason


def test_negative_duration():
    line = "2026-10-20T12:34:56Z INFO auth 192.0.2.10 POST /api/login 200 -5ms rid=ab12cd34"
    with pytest.raises(ParseError):
        parse_line(line)


def test_invalid_rid():
    line = "2026-10-20T12:34:56Z INFO auth 192.0.2.10 POST /api/login 200 43ms rid=ZZZ12CD3"
    with pytest.raises(ParseError):
        parse_line(line)


def test_empty_line():
    with pytest.raises(ParseError) as exc:
        parse_line("   ")
    assert "пустая" in exc.value.reason


def test_extra_whitespace_allowed():
    line = (
        "2026-10-20T12:34:56Z  INFO auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd34"
    )
    # Дополнительные пробелы допустимы (\s+), поэтому строка проходит.
    assert parse_line(line)["level"] == "INFO"


# --- Отдельные регулярные выражения (не менее трёх, каждое со своим тестом) ---


def test_ts_regex():
    assert TS_RE.fullmatch("2026-10-20T12:34:56Z")
    assert not TS_RE.fullmatch("2026-10-20 12:34:56")


def test_ipv4_regex():
    assert IPV4_RE.fullmatch("192.0.2.10")
    assert not IPV4_RE.fullmatch("999.1.1.1")


def test_rid_regex():
    assert RID_RE.fullmatch("ab12cd34")
    assert not RID_RE.fullmatch("ZZZ12CD3")


def test_path_regex():
    assert PATH_RE.fullmatch("/api/orders/42")
    assert not PATH_RE.fullmatch("api/orders")


def test_check_field_helper():
    assert check_field("rid", "ab12cd34")
    assert not check_field("ip", "999.1.1.1")


def test_find_problem_lines():
    text = f"{VALID_INFO}\n{VALID_ERROR}\n{VALID_WARN}\n"
    problems = find_problem_lines(text)
    assert len(problems) == 2
