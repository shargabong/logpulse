"""Точка входа FastAPI-приложения LogPulse."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .routers import router

app = FastAPI(
    title="LogPulse",
    version="1.0",
    description="Приём и разбор сервисных логов, статистика в Redis.",
)

app.include_router(router)

# Коды ошибок для единого формата ответа.
ERROR_TYPES = {404: "not_found", 422: "validation_error", 503: "service_unavailable"}


@app.exception_handler(StarletteHTTPException)
def http_error(request: Request, exc: StarletteHTTPException):
    """Оформить HTTP-ошибки в едином виде."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": ERROR_TYPES.get(exc.status_code, "http_error"),
                "message": str(exc.detail),
            }
        },
    )


@app.exception_handler(RequestValidationError)
def validation_error(request: Request, exc: RequestValidationError):
    """422 при неверной структуре запроса (без лишних деталей)."""
    details = [
        {"loc": [str(x) for x in e["loc"]], "msg": str(e["msg"]), "type": str(e["type"])}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "validation_error",
                "message": "ошибка структуры запроса",
                "details": details,
            }
        },
    )
