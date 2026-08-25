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


def _all_correct_seed_answers(exam_id: int) -> list[dict]:
    """Правильные ответы экзамена читаются из БД — тест не зависит от того,
    какие именно вопросы сгенерировал seed."""
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.domain.enums import QuestionType
    from app.domain.models import Question

    payload: list[dict] = []
    with SessionLocal() as db:
        questions = db.scalars(
            select(Question).where(Question.exam_id == exam_id).order_by(Question.id)
        ).all()
        for question in questions:
            correct = [a for a in question.answers if a.is_correct]
            ids: list[int] = []
            text = None
            if question.type == QuestionType.SINGLE:
                ids = [correct[0].id]
            elif question.type == QuestionType.MULTI:
                ids = sorted(a.id for a in correct)
            elif question.type == QuestionType.DND:
                # Порядок вставки ответов = правильная последовательность.
                ids = [a.id for a in correct]
            elif question.type == QuestionType.TEXT:
                text = correct[0].answer
            payload.append({"question_id": question.id, "answer_ids": ids, "text": text})
    return payload


def _exam_with_question_of_type(q_type: str) -> int:
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.domain.enums import QuestionType
    from app.domain.models import Question

    enum_type = QuestionType(q_type)
    with SessionLocal() as db:
        question = db.scalars(
            select(Question).where(Question.type == enum_type).order_by(Question.id)
        ).first()
        assert question is not None, f"seed не создал вопросов типа {q_type}"
        return question.exam_id


def test_passed_exam_updates_progress_and_creates_certificate(client, user_token):
    headers = auth(user_token)
    assert client.post("/api/courses/1/enroll", headers=headers).status_code == 200
    exam = client.get("/api/exams/1").json()

    result = client.post(
        "/api/exams/1/submit",
        headers=headers,
        json={"answers": _all_correct_seed_answers(exam["id"])},
    )

    assert result.status_code == 200
    assert result.json()["score"] == 100
    assert result.json()["certificate_url"] == "/certificates/exams/1"
    certificate = client.get(result.json()["certificate_url"], headers=headers)
    assert certificate.status_code == 200
    assert 'data-testid="certificate-score">100%' in certificate.text

    course = client.get("/courses/1", headers=headers)
    assert 'style="width: 100%"' in course.text


def test_dnd_answer_requires_correct_order(client, user_token):
    exam_id = _exam_with_question_of_type("DND")
    exam = client.get(f"/api/exams/{exam_id}").json()
    dnd = next(question for question in exam["questions"] if question["type"] == "DND")
    correct_order = [answer["id"] for answer in dnd["answers"]]

    wrong = client.post(
        f"/api/exams/{exam_id}/submit",
        headers=auth(user_token),
        json={"answers": [{
            "question_id": dnd["id"], "answer_ids": list(reversed(correct_order)), "text": None,
        }]},
    )
    right = client.post(
        f"/api/exams/{exam_id}/submit",
        headers=auth(user_token),
        json={"answers": [{
            "question_id": dnd["id"], "answer_ids": correct_order, "text": None,
        }]},
    )

    assert wrong.json()["correct"] == 0
    assert right.json()["correct"] == 1


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
