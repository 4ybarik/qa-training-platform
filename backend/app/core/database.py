"""Инфраструктура доступа к базе данных.

Здесь создаётся движок SQLAlchemy и фабрика сессий. Сессия выдаётся через
зависимость FastAPI (см. app/api/deps.py) и закрывается после каждого запроса.
"""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Для SQLite (тесты) нужен особый аргумент про потоки.
_connect_args = {}
if settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""


def get_db() -> Iterator[Session]:
    """Зависимость FastAPI: выдаёт сессию и гарантированно её закрывает."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Создаёт таблицы по метаданным моделей (используется при старте/тестах)."""
    # Импорт моделей обязателен, чтобы они зарегистрировались в метаданных.
    from app.domain import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
