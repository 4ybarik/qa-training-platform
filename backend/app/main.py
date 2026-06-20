"""Фабрика приложения FastAPI.

Собирает все слои: middleware, обработчики ошибок, API-роутеры, веб-интерфейс,
статику и WebSocket. На старте создаёт таблицы и (в dev) загружает seed-данные.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import auth, courses, exams, misc, playground
from app.api.errors import register_exception_handlers
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.middleware import PlaygroundMiddleware
from app.seed import seed
from app.web.router import router as web_router

settings = get_settings()
STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.environment == "development":
        with SessionLocal() as db:
            seed(db)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Учебная платформа для практики автоматизации тестирования.",
        lifespan=lifespan,
    )

    # Порядок важен: Starlette выполняет middleware в ОБРАТНОМ порядке
    # добавления (последний добавленный оборачивает остальные снаружи).
    # PlaygroundMiddleware добавляем первым, чтобы CORSMiddleware выполнялся
    # последним и успевал проставить CORS-заголовки даже на ответах 500,
    # которые Playground формирует напрямую, минуя остальной стек.
    app.add_middleware(PlaygroundMiddleware, state=playground.state)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # API
    app.include_router(auth.router)
    app.include_router(courses.router)
    app.include_router(exams.router)
    app.include_router(misc.profile_router)
    app.include_router(misc.notif_router)
    app.include_router(misc.admin_router)
    app.include_router(misc.health_router)
    app.include_router(playground.router)
    app.include_router(playground.ws_router)

    # Веб-интерфейс и статика
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(web_router)

    return app


app = create_app()
