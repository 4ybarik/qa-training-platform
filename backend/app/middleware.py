"""Middleware режима «Testing Playground».

Когда режим включён, к ответам API искусственно добавляются:
- задержки (latency);
- случайные ошибки 500 (с заданной вероятностью).

Это нужно автоматизаторам для тренировки устойчивости тестов (ожидания, ретраи).
Режим включается per-request заголовком X-Playground: on либо глобально в состоянии.
"""
import asyncio
import random

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class PlaygroundState:
    enabled: bool = False
    latency_ms: int = 800
    error_rate: float = 0.2  # 20% запросов вернут 500


class PlaygroundMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, state: PlaygroundState) -> None:
        super().__init__(app)
        self.state = state

    async def dispatch(self, request: Request, call_next):
        header = request.headers.get("X-Playground", "").lower()
        active = self.state.enabled or header == "on"

        # На сами эндпоинты управления, проверки состояния, статику и страницу
        # управления Playground хаос не наводим — иначе пользователь не сможет
        # быстро отключить режим, а интерфейс будет тормозить целиком.
        path = request.url.path
        excluded = (
            "/api/playground", "/health", "/liveness", "/readiness",
            "/static", "/playground",
        )
        if active and not path.startswith(excluded):
            if self.state.latency_ms:
                await asyncio.sleep(self.state.latency_ms / 1000)
            if request.url.path.startswith("/api") and random.random() < self.state.error_rate:
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Testing Playground: искусственная ошибка сервера"},
                )
        return await call_next(request)
