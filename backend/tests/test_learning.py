"""Сквозные проверки маршрута: урок → starter → run → прогресс."""
import pytest

from app.learning.catalog import lesson_for, lessons, render_micro_markdown
from app.learning.workspace import student_tests_dir
from app.practice.catalog import CHALLENGES_BY_SLUG


STUDENT_DIR = student_tests_dir()
STARTER_REL = "api/test_echo_contract.py"


@pytest.fixture(autouse=True)
def _cleanup_learning_starter():
    target = STUDENT_DIR / STARTER_REL
    original = target.read_bytes() if target.exists() else None
    target.unlink(missing_ok=True)
    yield
    target.unlink(missing_ok=True)
    if original is not None:
        target.write_bytes(original)


def _web_login(client):
    response = client.post(
        "/web/login",
        data={"email": "user@test.com", "password": "Password123!"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_every_challenge_has_micro_lesson_and_safe_rendering():
    items = lessons("ru")

    assert len(items) == 48
    assert all(item.theory_minutes == 5 and item.practice_minutes == 95 for item in items)
    echo = lesson_for(CHALLENGES_BY_SLUG["echo-contract"])
    rendered = str(render_micro_markdown('Текст <script>alert(1)</script>\n\n```python\nassert True\n```'))

    assert echo.editable_path == STARTER_REL
    assert "pytest.fail" in echo.starter_code
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "<pre><code" in rendered


def test_learning_api_requires_authentication_and_returns_progress(client):
    client.cookies.clear()
    unauthorized = client.get("/api/learning/progress")
    login = client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "Password123!"},
    )
    user_token = login.json()["access_token"]
    authorized = client.get(
        "/api/learning/catalog",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert authorized.json()["total"] == 48
    assert authorized.json()["items"][0]["progress"]["attempts"] == 0


def test_lesson_creates_starter_runs_and_records_attempt(client):
    _web_login(client)

    started = client.post("/web/learning/echo-contract/start", follow_redirects=False)
    assert started.status_code == 303
    assert started.headers["location"] == "/ide?file=api/test_echo_contract.py&challenge=echo-contract"
    starter = STUDENT_DIR / STARTER_REL
    assert starter.is_file()
    assert "TODO: реализуйте критерии задачи" in starter.read_text(encoding="utf-8")

    run = client.post(
        "/api/ide/run",
        json={"path": STARTER_REL, "challenge_slug": "echo-contract"},
    )
    assert run.status_code == 200, run.text
    body = run.json()
    assert body["passed"] is False
    assert body["score"] < 100
    assert body["criteria"][0]["code"] == "baseline"

    progress = client.get("/api/learning/progress").json()
    assert progress["summary"]["started"] == 1
    assert progress["items"]["echo-contract"]["attempts"] == 1
    assert progress["items"]["echo-contract"]["completed"] is False


def test_challenge_run_rejects_another_file(client):
    _web_login(client)
    response = client.post(
        "/api/ide/run",
        json={"path": "api/test_health_smoke.py", "challenge_slug": "echo-contract"},
    )

    assert response.status_code == 400
    assert "не соответствует" in response.json()["detail"]


def test_manager_can_view_learner_progress_but_user_cannot(client):
    _web_login(client)
    denied = client.get("/learning/manage")
    assert denied.status_code == 403

    client.cookies.clear()
    manager_login = client.post(
        "/web/login",
        data={"email": "manager@test.com", "password": "Password123!"},
        follow_redirects=False,
    )
    assert manager_login.status_code == 303
    page = client.get("/learning/manage")
    assert page.status_code == 200
    assert 'data-testid="learning-manage-table"' in page.text
    assert "user@test.com" in page.text
