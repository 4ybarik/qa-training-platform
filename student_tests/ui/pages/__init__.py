"""Page Object каркас для UI-тестов ученика.

Импортируйте готовые страницы или наследуйте от BasePage свои:

    from pages.login_page import LoginPage

    def test_something(login_page: LoginPage):
        login_page.open().login("user@test.com", "Password123!")
"""
from pages.base_page import BasePage
from pages.login_page import LoginPage

__all__ = ["BasePage", "LoginPage"]
