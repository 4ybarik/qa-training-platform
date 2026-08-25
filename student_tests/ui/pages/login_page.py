"""Page Object страницы входа (/login).

Пример разбора страницы на осмысленные действия: fill_email/fill_password —
атомарные шаги, login — готовый пользовательский сценарий. Локаторы собраны
в одном месте; если разработчики переименуют data-testid, вы поправите ровно
один файл.
"""
from playwright.sync_api import Page, expect

from pages.base_page import BasePage


class LoginPage(BasePage):
    path = "/login"

    # --- локаторы -----------------------------------------------------------
    def email_input(self):
        return self.page.get_by_test_id("email-input")

    def password_input(self):
        return self.page.get_by_test_id("password-input")

    def submit_button(self):
        return self.page.get_by_test_id("login-button")

    def error_message(self):
        return self.page.get_by_test_id("login-error")

    # --- атомарные действия -------------------------------------------------
    def fill_email(self, email: str) -> "LoginPage":
        self.email_input().fill(email)
        return self

    def fill_password(self, password: str) -> "LoginPage":
        self.password_input().fill(password)
        return self

    def submit(self) -> "LoginPage":
        self.submit_button().click()
        return self

    # --- готовые сценарии ---------------------------------------------------
    def login(self, email: str, password: str) -> Page:
        """Полный вход с валидными данными. Возвращает страницу дашборда."""
        self.fill_email(email).fill_password(password).submit()
        self.page.wait_for_url("**/dashboard")
        return self.page

    def expect_error_visible(self) -> None:
        """Проверка ошибки — допустима в POM как переиспользуемое утверждение."""
        expect(self.error_message()).to_be_visible()
