"""API-тесты каталога курсов и записи на курс."""
import uuid

from tests.conftest import auth


def test_list_courses_pagination(client):
    r = client.get("/api/courses", params={"page": 1, "size": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 1 and body["size"] == 5
    assert len(body["items"]) <= 5
    assert body["total"] >= 50


def test_search_courses(client):
    r = client.get("/api/courses", params={"q": "Playwright"})
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert "playwright" in item["title"].lower()


def test_sort_courses_by_price_desc(client):
    r = client.get("/api/courses", params={"sort": "price", "order": "desc", "size": 10})
    prices = [c["price"] for c in r.json()["items"]]
    assert prices == sorted(prices, reverse=True)


def test_categories(client):
    r = client.get("/api/courses/categories")
    assert r.status_code == 200
    assert len(r.json()) > 0


def test_get_course_not_found(client):
    assert client.get("/api/courses/999999").status_code == 404


def test_enroll_flow(client):
    # отдельный пользователь, чтобы запись была чистой
    email = f"enr_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    token = client.post("/api/auth/login",
                        json={"email": email, "password": "Password123!"}).json()["access_token"]

    first = client.post("/api/courses/1/enroll", headers=auth(token))
    assert first.status_code == 200
    # повторная запись запрещена
    second = client.post("/api/courses/1/enroll", headers=auth(token))
    assert second.status_code == 409


def test_enroll_requires_auth(client):
    assert client.post("/api/courses/1/enroll").status_code == 401


# ---------- CRUD курсов: только ADMIN ----------
def test_user_cannot_create_course(client, user_token):
    r = client.post("/api/courses", headers=auth(user_token),
                    json={"title": "Попытка обычного пользователя"})
    assert r.status_code == 403


def test_create_course_requires_auth(client):
    r = client.post("/api/courses", json={"title": "Без токена"})
    assert r.status_code == 401


def test_admin_can_create_update_delete_course(client, admin_token):
    create = client.post("/api/courses", headers=auth(admin_token), json={
        "title": "Временный курс для теста", "description": "тест",
        "price": 100, "category": "QA", "status": "PUBLISHED",
    })
    assert create.status_code == 201, create.text
    course_id = create.json()["id"]

    update = client.put(f"/api/courses/{course_id}", headers=auth(admin_token),
                        json={"title": "Обновлённое название"})
    assert update.status_code == 200
    assert update.json()["title"] == "Обновлённое название"

    delete = client.delete(f"/api/courses/{course_id}", headers=auth(admin_token))
    assert delete.status_code == 200

    # курс действительно удалён
    assert client.get(f"/api/courses/{course_id}").status_code == 404


def test_user_cannot_update_or_delete_course(client, user_token):
    assert client.put("/api/courses/1", headers=auth(user_token),
                      json={"title": "Хочу поменять"}).status_code == 403
    assert client.delete("/api/courses/1", headers=auth(user_token)).status_code == 403
