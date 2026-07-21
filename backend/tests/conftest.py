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
os.environ["SECRET_KEY"] = "test-secret-at-least-32-bytes-long!"
os.environ["ALLOW_TEST_MUTATIONS"] = "true"

# Чистим БД до старта сессии тестов.
if _TEST_DB.exists():
    _TEST_DB.unlink()

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.database import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    # Контекстный менеджер запускает lifespan: init_db + seed.
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clear_client_cookies(client):
    """Очищает cookies клиента перед каждым тестом.

    Клиент имеет scope="session" (один объект на все тесты — это специально,
    пересоздание TestClient с полным lifespan на каждый тест было бы дорого).
    Но /api/auth/login ВСЕГДА выставляет cookie access_token (она нужна для
    серверного веб-интерфейса — см. комментарий в app/api/auth.py). Если её
    не чистить, тест с логином "заражает" cookie все последующие тесты в той
    же сессии pytest, и тест вида "запрос без токена должен дать 401" может
    неожиданно пройти авторизованным через протёкшую cookie, а не упасть как
    ожидается. Поэтому перед КАЖДЫМ тестом куки сбрасываются на чистый лист;
    кто реально хочет быть авторизован — получает токен явно через
    user_token/admin_token и передаёт его заголовком (см. auth() ниже).
    """
    client.cookies.clear()
    yield
    client.cookies.clear()


@pytest.fixture(autouse=True)
def _rollback_database_after_test(client):
    """Каждый тест получает транзакцию, которая всегда откатывается.

    Приложение внутри теста может вызывать ``commit``: сессия привязана к уже
    открытой транзакции соединения, поэтому данные видны в текущем тесте, но не
    протекают в следующий. Seed остаётся за пределами этой транзакции.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


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
