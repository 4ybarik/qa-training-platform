"""Общие фикстуры пользовательских автотестов.

Все адреса и учётные данные читаются из окружения, поэтому те же тесты работают
из локальной IDE и во внутренней Docker-сети Jenkins.
"""
from collections.abc import Iterator
import os
import uuid

import httpx
import pytest
from axe_playwright_python.sync_playwright import Axe


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.getenv(
        "STUDENT_DATABASE_URL",
        "postgresql://qatp:qatp@localhost:5432/qatp",
    )


@pytest.fixture
def api_client(base_url: str) -> Iterator[httpx.Client]:
    default_headers = {}
    if mutation := os.getenv("TEST_MUTATION"):
        default_headers["X-Test-Mutation"] = mutation
    with httpx.Client(
        base_url=base_url,
        timeout=5.0,
        follow_redirects=False,
        headers=default_headers,
    ) as client:
        yield client


@pytest.fixture
def run_id() -> str:
    """Уникальный namespace исключает конфликты между тестами и сборками."""
    return f"pytest-{uuid.uuid4().hex}"


@pytest.fixture
def run_headers(api_client: httpx.Client, run_id: str) -> Iterator[dict[str, str]]:
    headers = {"X-Test-Run-Id": run_id}
    yield headers
    # Адресный teardown безопасен даже после частично упавшего теста.
    response = api_client.delete("/api/practice/state", headers=headers)
    if response.status_code not in {204, 404}:
        raise RuntimeError(f"Practice cleanup failed: {response.status_code} {response.text}")


@pytest.fixture
def integration_headers(api_client: httpx.Client, run_id: str) -> Iterator[dict[str, str]]:
    headers = {"X-Test-Run-Id": run_id}
    yield headers
    response = api_client.delete("/api/integrations/state", headers=headers)
    if response.status_code not in {204, 404}:
        raise RuntimeError(
            f"Integration cleanup failed: {response.status_code} {response.text}"
        )


@pytest.fixture
def test_support_headers(api_client: httpx.Client, run_id: str) -> Iterator[dict[str, str]]:
    """Доступ к dev-only Test Data API и гарантированная адресная очистка."""
    headers = {
        "X-Test-Run-Id": run_id,
        "X-Test-Support-Key": os.getenv("TEST_SUPPORT_KEY", "local-test-support-key"),
    }
    yield headers
    response = api_client.delete("/api/test-support/state", headers=headers)
    if response.status_code != 200:
        raise RuntimeError(f"Test data cleanup failed: {response.status_code} {response.text}")


@pytest.fixture
def user_factory(api_client: httpx.Client, test_support_headers: dict[str, str]):
    """Создаёт уникального пользователя, автоматически удаляемого после теста."""

    def create(**overrides):
        payload = {
            "password": "Password123!",
            "role": "USER",
            "first_name": "Auto",
            "last_name": "Test",
            **overrides,
        }
        response = api_client.post(
            "/api/test-support/users",
            headers=test_support_headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    return create


@pytest.fixture
def auth_headers(api_client: httpx.Client):
    """Возвращает Bearer-заголовок для пользователя из ``user_factory``."""

    def login_as(user: dict[str, str]) -> dict[str, str]:
        response = api_client.post(
            "/api/auth/login",
            json={"email": user["email"], "password": user["password"]},
        )
        response.raise_for_status()
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return login_as


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Передаёт выбранную контролируемую мутацию во все UI-запросы."""
    mutation = os.getenv("TEST_MUTATION")
    if not mutation:
        return browser_context_args
    headers = dict(browser_context_args.get("extra_http_headers", {}))
    headers["X-Test-Mutation"] = mutation
    return {**browser_context_args, "extra_http_headers": headers}


@pytest.fixture
def credentials() -> dict[str, str]:
    return {
        "email": os.getenv("TEST_USER_EMAIL", "user@test.com"),
        "password": os.getenv("TEST_USER_PASSWORD", "Password123!"),
    }


@pytest.fixture
def login(page, base_url: str, credentials: dict[str, str]):
    def perform_login():
        page.goto(f"{base_url}/login")
        page.get_by_test_id("email-input").fill(credentials["email"])
        page.get_by_test_id("password-input").fill(credentials["password"])
        page.get_by_test_id("login-button").click()
        page.wait_for_url("**/dashboard")
        return page

    return perform_login


@pytest.fixture(scope="session")
def axe() -> Axe:
    """axe-core scanner для автоматических WCAG-проверок."""
    return Axe()
