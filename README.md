# LogPulse

Небольшая система для приёма и разбора сервисных логов. Принимает строки
логов по HTTP, проверяет их регулярными выражениями, складывает корректные
события в Redis Stream, а отдельный воркер разбирает их и накапливает
статистику в Redis. Всё поднимается одним `docker compose`.

## Архитектура

Клиент -> API (FastAPI) -> Redis Stream (`logpulse:events`) -> Worker ->
Redis (Hash + Sorted Set). API также читает агрегаты из Redis для `/stats`.

![Архитектура](docs/architecture.png)

Редактируемый исходник схемы: [`architecture.drawio`](architecture.drawio)
(открывается в https://app.diagrams.net/).

## Состав компонентов

| Компонент | Каталог | Назначение |
| --- | --- | --- |
| API | `app/` | FastAPI: `/health`, `/ingest`, `/stats`, `/events`. Парсер и слой Redis. |
| Парсер | `app/parser.py` | Разбор строки одной регуляркой с именованными группами + отдельные проверки полей. |
| Worker | `worker/worker.py` | Читает поток через `XREADGROUP`, обновляет статистику, подтверждает через `XACK`. |
| Данные | `data/sample.log` | 45 корректных строк и 6 намеренно испорченных. |
| Тесты | `tests/` | 37 тестов pytest. |
| Инфраструктура | `Dockerfile`, `compose.yaml`, `.env.example` | Три сервиса: `api`, `worker`, `redis`. |

## Запуск через Docker Compose

```bash
cp .env.example .env            # при необходимости поправьте значения
docker compose up --build -d
docker compose ps
docker compose logs --tail=50 api worker redis
```

API поднимется на `127.0.0.1:8000` (порт можно изменить через `API_PORT`).
Swagger UI: http://127.0.0.1:8000/docs

Если порт 8000 занят, например другим проектом:

```bash
API_PORT=8080 docker compose up --build -d
```

Остановить (данные сохраняются в volume `redis-data`):

```bash
docker compose down
```

> `docker compose down -v` удаляет volume вместе с данными. Не используйте его,
> если проверяете сохранность статистики.

## Локальный запуск без Docker

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt   # Windows
export REDIS_URL=redis://localhost:6379/0

uvicorn app.main:app --reload
python -m worker.worker        # в отдельном терминале
```

## Примеры запросов

Проверка доступности:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok","redis":"ok"}
```

Приём пакета строк (3 корректные + 2 ошибочные):

```bash
curl -X POST http://127.0.0.1:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"lines":[
    "2026-10-20T12:34:56Z INFO auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd34",
    "2026-10-20T12:34:58Z ERROR orders 198.51.100.8 GET /api/orders 503 742ms rid=ee44cc22",
    "2026-10-20T12:35:01Z WARN payment 203.0.113.7 POST /api/pay 429 301ms rid=ff44aa33",
    "2026-10-20T12:35:04Z ERROR orders 198.51.100.8 GET /api/orders 999 100ms rid=aa11bb22",
    "2026-10-20T12:35:07Z INFO auth 999.1.1.1 POST /api/login 200 43ms rid=cc33dd44"
  ]}'
```

Ответ: `accepted=3`, `rejected=2` и пояснения по двум ошибкам.

Статистика и последние события:

```bash
curl http://127.0.0.1:8000/stats
curl "http://127.0.0.1:8000/events?limit=3"
```

Полностью сквозной сценарий: `python tools/smoke.py`.

## Структуры Redis

| Ключ | Тип | Запись | Чтение | Назначение |
| --- | --- | --- | --- | --- |
| `logpulse:events` | Stream | `XADD` | `XREADGROUP`, `XREVRANGE` | Очередь событий |
| `logpulse:stats:level` | Hash | `HINCRBY` | `HGETALL` | Счётчики уровней |
| `logpulse:stats:service` | Hash | `HINCRBY` | `HGETALL` | Счётчики сервисов |
| `logpulse:stats:status` | Hash | `HINCRBY` | `HGETALL` | Счётчики HTTP-кодов |
| `logpulse:slow` | Sorted Set | `ZADD` | `ZREVRANGE` | ТОП медленных запросов |
| `logpulse:processed` | Set | `SADD` | `SISMEMBER` | Идемпотентность повторной доставки |

Порог медленного запроса: `duration_ms >= 500` (`SLOW_THRESHOLD_MS`).

## Pydantic-модели

- `IngestRequest` — `lines`: от 1 до 100 строк, каждая длиной 1-500 символов.
- `IngestResponse` — `accepted`, `rejected`, `errors[]` (номер строки и причина).
- `StatsResponse` — `total`, `by_level`, `by_service`, `by_status`, `top_slow[]`.
- `EventsResponse` — `count`, `events[]`.
- `HealthResponse` — `status`, `redis`.
- `ErrorResponse` — единый формат ошибок: `{"error": {"type", "message", "details"}}`.

Ошибки: `422` при неверной структуре запроса, `503` при недоступности Redis.
Трассировки и секреты наружу не отдаются.

## Тесты

```bash
pytest -q                                   # локально
docker compose exec api pytest -q           # внутри контейнера
```

Redis-зависимость подменяется через `app.dependency_overrides`, поэтому тесты
не портят рабочие данные.

## Ограничения

- Идемпотентность обеспечивается множеством `logpulse:processed`: при большом
  потоке оно растёт. Для продакшена стоит ограничивать его по времени (`EXPIRE`)
  или перейти на дедупликацию по бизнес-ключу.
- При полном удалении DNS-имени сервиса `redis` (команда `stop`, а не
  `restart`) в логах API появляется косметический `Future exception was never
  retrieved` от redis-py. На работу не влияет: клиент переподключается.
- Воркер читает по одной группе потребителей без претензий на шардирование.
