"""Преобразование доменных исключений в HTTP-ответы."""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.errors import (
    AuthError, ConflictError, NotFoundError, PermissionError_, RateLimitError,
)

_MAP = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    AuthError: status.HTTP_401_UNAUTHORIZED,
    PermissionError_: status.HTTP_403_FORBIDDEN,
    RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
}


def register_exception_handlers(app: FastAPI) -> None:
    for exc_type, code in _MAP.items():
        app.add_exception_handler(exc_type, _make_handler(code))


def _make_handler(code: int):
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=code, content={"detail": str(exc)})

    return handler
