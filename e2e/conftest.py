"""Фикстуры E2E-тестов Playwright.

BASE_URL берётся из переменной окружения (по умолчанию локальный сервер).
"""
import os

import pytest

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture
def login(page, base_url):
    """Выполняет вход под демо-пользователем и возвращает страницу на дашборде."""
    def _login(email: str = "user@test.com", password: str = "Password123!"):
        page.goto(f"{base_url}/login")
        page.get_by_test_id("email-input").fill(email)
        page.get_by_test_id("password-input").fill(password)
        page.get_by_test_id("login-button").click()
        page.wait_for_url("**/dashboard")
        return page
    return _login
