"""API-тесты администрирования: пользователи, активация, уведомления, аудит."""
import uuid

from tests.conftest import auth


def _create_user(client, prefix="adm") -> tuple[str, int]:
    """Регистрирует нового пользователя и возвращает (email, id)."""
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@test.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    assert r.status_code == 201, r.text
    return email, r.json()["id"]


def test_user_cannot_list_users(client, user_token):
    assert client.get("/api/admin/users", headers=auth(user_token)).status_code == 403


def test_admin_can_list_users(client, admin_token):
    r = client.get("/api/admin/users", headers=auth(admin_token))
    assert r.status_code == 200
    assert len(r.json()) > 0


def test_admin_can_deactivate_and_reactivate_user(client, admin_token):
    _, uid = _create_user(client)

    deactivate = client.put(f"/api/admin/users/{uid}/active", headers=auth(admin_token),
                            json={"is_active": False})
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False

    reactivate = client.put(f"/api/admin/users/{uid}/active", headers=auth(admin_token),
                            json={"is_active": True})
    assert reactivate.status_code == 200
    assert reactivate.json()["is_active"] is True


def test_deactivated_user_cannot_login(client, admin_token):
    email, uid = _create_user(client)
    client.put(f"/api/admin/users/{uid}/active", headers=auth(admin_token), json={"is_active": False})

    login = client.post("/api/auth/login", json={"email": email, "password": "Password123!"})
    assert login.status_code == 401


def test_admin_cannot_deactivate_self(client, admin_token):
    me = client.get("/api/auth/me", headers=auth(admin_token)).json()
    r = client.put(f"/api/admin/users/{me['id']}/active", headers=auth(admin_token),
                   json={"is_active": False})
    assert r.status_code == 403


def test_user_cannot_change_roles(client, user_token):
    r = client.put("/api/admin/users/1/role", headers=auth(user_token), json={"role": "ADMIN"})
    assert r.status_code == 403


# ---------- Уведомления администратора ----------
def test_user_cannot_send_admin_notification(client, user_token):
    r = client.post("/api/admin/notifications", headers=auth(user_token),
                    json={"message": "Попытка обычного пользователя"})
    assert r.status_code == 403


def test_admin_can_send_notification_to_specific_user(client, admin_token):
    _, uid = _create_user(client)
    r = client.post("/api/admin/notifications", headers=auth(admin_token),
                    json={"user_id": uid, "message": "Личное уведомление"})
    assert r.status_code == 201
    body = r.json()
    assert len(body) == 1
    assert body[0]["message"] == "Личное уведомление"


def test_admin_broadcast_notification_reaches_multiple_users(client, admin_token):
    r = client.post("/api/admin/notifications", headers=auth(admin_token),
                    json={"message": "Рассылка всем"})
    assert r.status_code == 201
    assert len(r.json()) > 1


def test_admin_notification_to_missing_user_404(client, admin_token):
    r = client.post("/api/admin/notifications", headers=auth(admin_token),
                    json={"user_id": 999999, "message": "Кому-то несуществующему"})
    assert r.status_code == 404


# ---------- Аудит ----------
def test_user_cannot_see_audit_log(client, user_token):
    assert client.get("/api/admin/audit", headers=auth(user_token)).status_code == 403


def test_admin_can_see_audit_log(client, admin_token):
    r = client.get("/api/admin/audit", headers=auth(admin_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)
