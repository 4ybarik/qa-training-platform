"""API-тесты аутентификации и авторизации."""
import uuid

from tests.conftest import auth


def test_login_success(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@test.com", "password": "Password123!"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@test.com", "password": "wrong"})
    assert r.status_code == 401


def test_register_and_me(client):
    email = f"new_{uuid.uuid4().hex[:8]}@test.com"
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "Password123!",
                          "first_name": "Тест", "last_name": "Юзер"})
    assert r.status_code == 201, r.text
    assert r.json()["email"] == email

    login = client.post("/api/auth/login", json={"email": email, "password": "Password123!"})
    token = login.json()["access_token"]
    me = client.get("/api/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_register_duplicate(client):
    r = client.post("/api/auth/register",
                    json={"email": "admin@test.com", "password": "Password123!"})
    assert r.status_code == 409


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_cookie_based_auth_can_be_cleared(client):
    """Подтверждает механизм, на котором держится межтестовая изоляция:
    client.cookies.clear() (то же самое, что делает autouse-фикстура
    _clear_client_cookies в conftest.py перед каждым тестом) реально убирает
    cookie-авторизацию. Самодостаточный тест — не зависит от порядка
    выполнения соседних тестов, в отличие от проверки "протекла ли cookie
    из предыдущего теста", которая зависела бы от того, что именно
    выполнялось до него.
    """
    login = client.post("/api/auth/login",
                        json={"email": "user@test.com", "password": "Password123!"})
    assert login.status_code == 200
    assert "access_token" in client.cookies

    # Без заголовка, но с cookie — легитимно авторизован (это не баг,
    # см. докстринг app/api/deps.py про два способа передачи токена).
    assert client.get("/api/auth/me").status_code == 200

    # Очищаем cookies тем же способом, что и autouse-фикстура между тестами.
    client.cookies.clear()
    assert "access_token" not in client.cookies

    # После очистки запрос без заголовка должен снова требовать авторизацию.
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_valid_token(client, user_token):
    r = client.get("/api/auth/me", headers=auth(user_token))
    assert r.status_code == 200


def test_refresh_token(client):
    login = client.post("/api/auth/login",
                        json={"email": "user@test.com", "password": "Password123!"})
    refresh = login.json()["refresh_token"]
    r = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_admin_only_endpoint_forbidden_for_user(client, user_token):
    r = client.get("/api/admin/users", headers=auth(user_token))
    assert r.status_code == 403


def test_admin_endpoint_allowed_for_admin(client, admin_token):
    r = client.get("/api/admin/users", headers=auth(admin_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)
