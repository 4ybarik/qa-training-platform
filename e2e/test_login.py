"""E2E: сценарии входа в систему."""
from playwright.sync_api import expect


def test_successful_login(page, base_url):
    page.goto(f"{base_url}/login")
    page.get_by_test_id("email-input").fill("admin@test.com")
    page.get_by_test_id("password-input").fill("Password123!")
    page.get_by_test_id("login-button").click()
    page.wait_for_url("**/dashboard")
    expect(page.get_by_test_id("dashboard-title")).to_be_visible()
    expect(page.get_by_test_id("current-user-role")).to_have_text("ADMIN")


def test_login_with_wrong_password_shows_error(page, base_url):
    page.goto(f"{base_url}/login")
    page.get_by_test_id("email-input").fill("admin@test.com")
    page.get_by_test_id("password-input").fill("wrong-password")
    page.get_by_test_id("login-button").click()
    expect(page.get_by_test_id("login-error")).to_be_visible()


def test_admin_sees_admin_nav(login):
    page = login("admin@test.com")
    expect(page.get_by_test_id("nav-admin")).to_be_visible()


def test_user_does_not_see_admin_nav(login):
    page = login("user@test.com")
    expect(page.get_by_test_id("nav-admin")).to_have_count(0)
