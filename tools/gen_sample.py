"""Генератор синтетического data/sample.log.

Скрипт детерминированный: при повторном запуске даёт тот же файл.
Валидные строки — с уникальными rid; отдельно добавлены намеренно
испорченные записи. Персональные данные и секреты не используются.

Запуск: python tools/gen_sample.py
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sample.log"

SERVICES = ["auth", "orders", "payment"]
LEVELS = ["INFO", "WARN", "ERROR"]
METHODS = ["GET", "POST", "PUT", "DELETE"]
PATHS = {
    "auth": ["/api/login", "/api/logout", "/api/token", "/api/refresh"],
    "orders": ["/api/orders", "/api/orders/42", "/api/orders/100", "/api/orders/7"],
    "payment": ["/api/pay", "/api/refund", "/api/methods", "/api/pay/status"],
}
IPS = ["192.0.2.10", "198.51.100.8", "203.0.113.7", "192.0.2.44", "198.51.100.21"]
STATUSES = [200, 201, 204, 301, 400, 401, 403, 404, 429, 500, 502, 503]
DURATIONS = [12, 43, 88, 120, 210, 301, 455, 520, 742, 980, 1500]


def make_valid_line(index: int) -> str:
    start = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)
    ts = (start + timedelta(seconds=index * 3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    service = SERVICES[index % len(SERVICES)]
    level = LEVELS[index % len(LEVELS)]
    method = METHODS[index % len(METHODS)]
    path = PATHS[service][index % len(PATHS[service])]
    ip = IPS[index % len(IPS)]
    status = STATUSES[index % len(STATUSES)]
    duration = DURATIONS[index % len(DURATIONS)]
    rid = f"{index + 1:08x}"
    return f"{ts} {level} {service} {ip} {method} {path} {status} {duration}ms rid={rid}"


# Намеренно испорченные строки (6 штук).
BROKEN = [
    "2026-13-45T99:99:99Z INFO auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd34",
    "2026-10-20T12:40:00Z INFO auth 999.1.1.1 POST /api/login 200 43ms rid=ab12cd35",
    "2026-10-20T12:40:03Z DEBUG auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd36",
    "2026-10-20T12:40:06Z ERROR orders 198.51.100.8 GET /api/orders 999 742ms rid=ab12cd37",
    "2026-10-20T12:40:09Z INFO payment 203.0.113.7 POST /api/pay 200 -5ms rid=ab12cd38",
    "2026-10-20T12:40:12Z WARN orders 198.51.100.8 GET /api/orders 500 742ms rid=ZZZ12cd3",
]

VALID_COUNT = 45


def main() -> None:
    lines = [make_valid_line(i) for i in range(VALID_COUNT)]
    # Вставляем испорченные строки ближе к концу файла.
    lines.extend(BROKEN)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Записано {len(lines)} строк в {OUT}")
    print(f"Валидных: {VALID_COUNT}, испорченных: {len(BROKEN)}")


if __name__ == "__main__":
    main()
