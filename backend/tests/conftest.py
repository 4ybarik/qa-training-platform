"""Общие фикстуры тестов.

Тесты идут против изолированной БД SQLite. Переменные окружения задаются ДО
импорта приложения, чтобы движок SQLAlchemy создался уже с тестовой БД.
"""
import os
import pathlib

import pytest

_TEST_DB = pathlib.Path(__file__).resolve().parent / "test.db"

os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEST_DB}")
os.environ.setdefault("ENVIRONMENT", "development")  # включает seed на старте
os.environ.setdefault("SECRET_KEY", "test-secret")

# Чистим БД до старта сессии тестов.
if _TEST_DB.exists():
    _TEST_DB.unlink()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    # Контекстный менеджер запускает lifespan: init_db + seed.
    with TestClient(app) as c:
        yield c


@pytest.fixture
def user_token(client) -> str:
    r = client.post("/api/auth/login",
                    json={"email": "user@test.com", "password": "Password123!"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def admin_token(client) -> str:
    r = client.post("/api/auth/login",
                    json={"email": "admin@test.com", "password": "Password123!"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
