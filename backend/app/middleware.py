"""Middleware режима «Testing Playground».

Когда режим включён, к ответам API искусственно добавляются:
- задержки (latency);
- случайные ошибки 500 (с заданной вероятностью).

Это нужно автоматизаторам для тренировки устойчивости тестов (ожидания, ретраи).
Для воспроизводимых тестов предпочтителен заголовок X-Playground-Scenario.
Старый вероятностный режим X-Playground: on сохранён как отдельное упражнение.
"""
import asyncio
import random
from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class CookieCSRFMiddleware(BaseHTTPMiddleware):
    """Блокирует межсайтовые изменения, когда JWT передан браузерной cookie."""

    _UNSAFE = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    async def dispatch(self, request: Request, call_next):
        bearer = request.headers.get("Authorization", "").lower().startswith("bearer ")
        cookie_authenticated = bool(request.cookies.get("access_token")) and not bearer
        if request.method in self._UNSAFE and cookie_authenticated:
            if request.headers.get("Sec-Fetch-Site", "").lower() == "cross-site":
                return JSONResponse(status_code=403, content={"detail": "Cross-site request blocked"})
            if origin := request.headers.get("Origin"):
                parts = urlsplit(origin)
                if parts.scheme not in {"http", "https"} or parts.netloc != request.url.netloc:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Origin does not match application host"},
                    )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Базовые защитные заголовки без нарушения учебных iframe и CDN IDE."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response


class PlaygroundState:
    enabled: bool = False
    latency_ms: int = 800
    error_rate: float = 0.2  # 20% запросов вернут 500


class PlaygroundMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, state: PlaygroundState) -> None:
        super().__init__(app)
        self.state = state
        self._seen_runs: set[str] = set()

    @staticmethod
    def _latency(request: Request, default: int) -> int:
        try:
            value = int(request.headers.get("X-Playground-Latency-Ms", default))
        except ValueError:
            value = default
        return min(max(value, 0), 5_000)

    async def dispatch(self, request: Request, call_next):
        header = request.headers.get("X-Playground", "").lower()
        active = self.state.enabled or header == "on"
        scenario = request.headers.get("X-Playground-Scenario", "").strip().lower()

        # На сами эндпоинты управления, проверки состояния, статику и страницу
        # управления Playground хаос не наводим — иначе пользователь не сможет
        # быстро отключить режим, а интерфейс будет тормозить целиком.
        path = request.url.path
        excluded = (
            "/api/playground", "/health", "/liveness", "/readiness",
            "/static", "/playground",
        )
        if path.startswith(excluded):
            return await call_next(request)

        if scenario:
            latency_ms = self._latency(request, self.state.latency_ms)
            if scenario in {"slow", "fail", "fail-first", "malformed-json"} and latency_ms:
                await asyncio.sleep(latency_ms / 1000)

            if scenario == "fail" and path.startswith("/api"):
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Testing Playground: deterministic server error"},
                )
            if scenario == "fail-first" and path.startswith("/api"):
                run_id = request.headers.get("X-Playground-Run", "").strip()
                if not run_id:
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "X-Playground-Run is required for fail-first"},
                    )
                key = f"{run_id}:{request.method}:{path}"
                if key not in self._seen_runs:
                    if len(self._seen_runs) >= 1_000:
                        self._seen_runs.clear()
                    self._seen_runs.add(key)
                    return JSONResponse(
                        status_code=503,
                        content={"detail": "Testing Playground: first attempt failed"},
                        headers={"Retry-After": "0"},
                    )
            if scenario == "malformed-json" and path.startswith("/api"):
                return Response(
                    content=b'{"detail": "truncated"',
                    status_code=200,
                    media_type="application/json",
                )

        if active:
            if self.state.latency_ms:
                await asyncio.sleep(self.state.latency_ms / 1000)
            if path.startswith("/api") and random.random() < self.state.error_rate:
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Testing Playground: artificial server error"},
                )
        return await call_next(request)
