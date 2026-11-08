"""Тесты парсера и регулярных выражений."""

import pytest

from app.parser import (
    IPV4_RE,
    PATH_RE,
    PROBLEM_RE,
    RID_RE,
    TS_RE,
    ParseError,
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
    e = parse_line(VALID_INFO)
    assert e["level"] == "INFO"
    assert e["service"] == "auth"
    assert e["path"] == "/api/login"
    assert e["status"] == 200
    assert e["rid"] == "ab12cd34"


def test_parse_valid_error():
    e = parse_line(VALID_ERROR)
    assert e["level"] == "ERROR"
    assert e["status"] == 503
    assert e["duration_ms"] == 742


def test_parse_valid_warn():
    e = parse_line(VALID_WARN)
    assert e["level"] == "WARN"
    assert e["ip"] == "203.0.113.7"


def test_numbers_are_int():
    e = parse_line(VALID_INFO)
    assert isinstance(e["status"], int)
    assert isinstance(e["duration_ms"], int)


def test_broken_timestamp():
    line = "2026-13-45T99:99:99Z INFO auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd34"
    with pytest.raises(ParseError) as exc:
        parse_line(line)
    assert "timestamp" in str(exc.value)


def test_invalid_ipv4():
    line = "2026-10-20T12:34:56Z INFO auth 999.1.1.1 POST /api/login 200 43ms rid=ab12cd34"
    with pytest.raises(ParseError) as exc:
        parse_line(line)
    assert "IP" in str(exc.value)


@pytest.mark.parametrize("level", ["DEBUG", "TRACE", "FATAL"])
def test_unsupported_level(level):
    line = f"2026-10-20T12:34:56Z {level} auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd34"
    with pytest.raises(ParseError):
        parse_line(line)


def test_invalid_status():
    line = "2026-10-20T12:34:56Z ERROR orders 198.51.100.8 GET /api/orders 999 742ms rid=ee44cc22"
    with pytest.raises(ParseError) as exc:
        parse_line(line)
    assert "код ответа" in str(exc.value)


def test_duration_out_of_range():
    line = "2026-10-20T12:34:56Z INFO auth 192.0.2.10 POST /api/login 200 700000ms rid=ab12cd34"
    with pytest.raises(ParseError) as exc:
        parse_line(line)
    assert "длительность" in str(exc.value)


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
    assert "пустая" in str(exc.value)


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


def test_problem_regex():
    assert PROBLEM_RE.search(VALID_ERROR)
    assert PROBLEM_RE.search(VALID_WARN)
    assert not PROBLEM_RE.search(VALID_INFO)


def test_find_problem_lines():
    text = VALID_INFO + "\n" + VALID_ERROR + "\n" + VALID_WARN + "\n"
    assert len(find_problem_lines(text)) == 2
