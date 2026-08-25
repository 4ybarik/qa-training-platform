"""ОБРАЗЕЦ: UI-тест через Page Object на примере страницы входа.

Это работающий тест — запускайте его и используйте как шпаргалку для своих
UI-задач из каталога (раздел «UI и Playwright»).

Продемонстрировано:
1. Page Object вместо «сырых» локаторов в тесте (см. ui/pages/login_page.py);
2. позитивный и негативный сценарий одной страницы рядом;
3. web-first утверждения expect() вместо wait_for_timeout/sleep.

Запуск:
  pip install -r student_tests/requirements.txt && playwright install chromium
  BASE_URL=http://localhost:8000 python -m pytest student_tests/ui/test_example_page_object.py -v
"""
import pytest
from pages.login_page import LoginPage
from playwright.sync_api import Page

DEMO_USER = {"email": "user@test.com", "password": "Password123!"}


@pytest.fixture
def login_page(page: Page, base_url: str) -> LoginPage:
    """Готовая страница входа. Фикстура page приходит из pytest-playwright."""
    return LoginPage(page, base_url)


@pytest.mark.ui
def test_login_success_opens_dashboard(login_page: LoginPage):
    dashboard = login_page.open().login(**DEMO_USER)

    # Оказались на дашборде — самый дешёвый признак успешного входа.
    assert "/dashboard" in dashboard.url


@pytest.mark.ui
def test_login_with_wrong_password_shows_error(login_page: LoginPage):
    login_page.open().fill_email(DEMO_USER["email"]).fill_password("wrong-password").submit()

    # Негативные проверки не менее важны: система должна явно сообщать об ошибке.
    login_page.expect_error_visible()
