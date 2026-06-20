"""API-тесты экзаменов и проверки состояния."""
from tests.conftest import auth


def test_get_exam_with_questions(client):
    r = client.get("/api/exams/1")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == 1
    assert len(body["questions"]) == 5
    # ответы не раскрывают признак правильности
    first_answer = body["questions"][0]["answers"][0]
    assert "is_correct" not in first_answer


def test_submit_exam_all_correct(client, user_token):
    exam = client.get("/api/exams/1").json()
    # Восстановить правильные ответы из API нельзя — отправим заведомо
    # корректные по структуре данные и проверим, что оценка считается.
    answers = []
    for q in exam["questions"]:
        if q["type"] == "TEXT":
            answers.append({"question_id": q["id"], "answer_ids": [], "text": "data-testid"})
        else:
            ids = [a["id"] for a in q["answers"]]
            answers.append({"question_id": q["id"], "answer_ids": ids, "text": None})
    r = client.post("/api/exams/1/submit", headers=auth(user_token),
                    json={"answers": answers})
    assert r.status_code == 200
    result = r.json()
    assert result["total"] == 5
    assert 0 <= result["score"] <= 100
    assert isinstance(result["passed"], bool)


def test_submit_requires_auth(client):
    assert client.post("/api/exams/1/submit", json={"answers": []}).status_code == 401


# ---------- CRUD экзаменов: только ADMIN ----------
def test_user_cannot_create_exam(client, user_token):
    r = client.post("/api/courses/1/exams", headers=auth(user_token),
                    json={"title": "Попытка", "questions": []})
    assert r.status_code == 403


def test_admin_can_create_update_delete_exam(client, admin_token):
    create = client.post("/api/courses/1/exams", headers=auth(admin_token), json={
        "title": "Временный экзамен", "duration_minutes": 10,
        "questions": [{
            "question": "2 + 2 = ?", "type": "SINGLE",
            "answers": [{"answer": "4", "is_correct": True}, {"answer": "5", "is_correct": False}],
        }],
    })
    assert create.status_code == 201, create.text
    exam_id = create.json()["id"]
    assert create.json()["questions"][0]["answers"][0]["is_correct"] is True

    update = client.put(f"/api/exams/{exam_id}", headers=auth(admin_token),
                        json={"title": "Обновлённый экзамен"})
    assert update.status_code == 200
    assert update.json()["title"] == "Обновлённый экзамен"

    delete = client.delete(f"/api/exams/{exam_id}", headers=auth(admin_token))
    assert delete.status_code == 200
    assert client.get(f"/api/exams/{exam_id}").status_code == 404


def test_create_exam_for_missing_course_404(client, admin_token):
    r = client.post("/api/courses/999999/exams", headers=auth(admin_token),
                    json={"title": "Экзамен для несуществующего курса", "questions": []})
    assert r.status_code == 404


def test_user_cannot_see_admin_exam_view(client, user_token):
    assert client.get("/api/exams/1/admin", headers=auth(user_token)).status_code == 403


def test_admin_exam_view_exposes_is_correct(client, admin_token):
    r = client.get("/api/exams/1/admin", headers=auth(admin_token))
    assert r.status_code == 200
    first_answer = r.json()["questions"][0]["answers"][0]
    assert "is_correct" in first_answer


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "version" in body and body["version"]


def test_liveness(client):
    assert client.get("/liveness").status_code == 200


def test_readiness(client):
    assert client.get("/readiness").json()["status"] == "ready"
