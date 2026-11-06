"""Сквозная проверка запущенного LogPulse.

Читает data/sample.log, отправляет строки в POST /ingest, ждёт обработки
воркером и запрашивает /stats и /events.

Запуск::

    python tools/smoke.py            # http://127.0.0.1:8000
    API_URL=http://127.0.0.1:8080 python tools/smoke.py
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")


def main() -> None:
    lines = (ROOT / "data" / "sample.log").read_text(encoding="utf-8").splitlines()
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        health = client.get("/health")
        print("GET /health ->", health.status_code, health.json())

        ingest = client.post("/ingest", json={"lines": lines})
        print("POST /ingest ->", ingest.status_code)
        print(json.dumps(ingest.json(), ensure_ascii=False, indent=2))

        # Небольшая пауза, чтобы воркер успел обработать поток.
        time.sleep(2.0)

        stats = client.get("/stats")
        print("GET /stats ->", stats.status_code)
        print(json.dumps(stats.json(), ensure_ascii=False, indent=2))

        events = client.get("/events", params={"limit": 3})
        print("GET /events?limit=3 ->", events.status_code)
        print(json.dumps(events.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
