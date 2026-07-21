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


def test_web_registration_persists_selected_practice_profile(client):
    email = f"web_{uuid.uuid4().hex[:8]}@test.com"
    response = client.post("/web/register", data={
        "email": email,
        "password": "Password123!",
        "confirm": "Password123!",
        "first_name": "Анна",
        "last_name": "Тестова",
        "birthday": "1995-06-15",
        "track": "api",
        "experience": "middle",
        "agree": "on",
    }, follow_redirects=False)
    assert response.status_code == 303

    token = client.post(
        "/api/auth/login", json={"email": email, "password": "Password123!"}
    ).json()["access_token"]
    profile = client.get("/api/profile", headers=auth(token)).json()
    assert profile["birthday"] == "1995-06-15"
    assert profile["skills"] == ["Track:api", "Experience:middle"]


def test_web_registration_requires_terms_server_side(client):
    response = client.post("/web/register", data={
        "email": f"terms_{uuid.uuid4().hex[:8]}@test.com",
        "password": "Password123!",
        "confirm": "Password123!",
        "track": "ui",
    })
    assert response.status_code == 400
    assert "Необходимо принять условия" in response.text


def test_direct_password_reset_changes_password(client):
    email = f"reset_{uuid.uuid4().hex[:8]}@test.com"
    old_password = "Password123!"
    new_password = "NewPassword456!"
    registered = client.post(
        "/api/auth/register",
        json={"email": email, "password": old_password},
    )
    assert registered.status_code == 201

    page = client.get("/forgot-password")
    assert page.status_code == 200
    assert 'data-testid="password-reset-form"' in page.text

    reset = client.post(
        "/web/forgot-password",
        data={
            "email": email,
            "new_password": new_password,
            "confirm_password": new_password,
        },
        follow_redirects=False,
    )
    assert reset.status_code == 303
    assert reset.headers["location"] == "/login?reset=success"

    success_page = client.get(reset.headers["location"])
    assert 'data-testid="password-reset-success"' in success_page.text

    old_login = client.post("/api/auth/login", json={"email": email, "password": old_password})
    new_login = client.post("/api/auth/login", json={"email": email, "password": new_password})
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_direct_password_reset_validates_confirmation_and_user(client):
    mismatch = client.post(
        "/web/forgot-password",
        data={
            "email": "user@test.com",
            "new_password": "NewPassword456!",
            "confirm_password": "Different456!",
        },
    )
    unknown = client.post(
        "/web/forgot-password",
        data={
            "email": f"missing_{uuid.uuid4().hex[:8]}@test.com",
            "new_password": "NewPassword456!",
            "confirm_password": "NewPassword456!",
        },
    )

    assert mismatch.status_code == 400
    assert "Пароли не совпадают" in mismatch.text
    assert unknown.status_code == 404
    assert "Пользователь с таким email не найден" in unknown.text


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
