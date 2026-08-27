"""Проверка успешной авторизации через пользовательский интерфейс."""
import pytest
from playwright.sync_api import expect


@pytest.mark.ui
def test_authorized_user_opens_dashboard(page, base_url, credentials):
    page.goto(f"{base_url}/login")
    page.get_by_test_id("email-input").fill(credentials["email"])
    page.get_by_test_id("password-input").fill(credentials["password"])
    page.get_by_test_id("login-button").click()

    expect(page).to_have_url(f"{base_url}/dashboard")
    expect(page.get_by_test_id("current-user-email")).to_have_text(credentials["email"])
