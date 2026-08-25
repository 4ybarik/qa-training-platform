"""Тесты встроенной IDE: файлы решений, запуск тестов, поиск локаторов."""
from pathlib import Path

import pytest

STUDENT_DIR = Path(__file__).resolve().parents[2] / "student_tests"
TMP_REL = "api/test_tmp_ide_demo.py"


@pytest.fixture()
def tmp_solution():
    """Создаёт временный файл решения и удаляет его после теста."""
    content = (
        "import pytest\n\n\n"
        "@pytest.mark.api\n"
        "def test_tmp_ide_demo_smoke():\n"
        "    assert 2 + 2 == 4\n"
    )
    (STUDENT_DIR / TMP_REL).write_text(content, encoding="utf-8")
    yield TMP_REL
    (STUDENT_DIR / TMP_REL).unlink(missing_ok=True)


def test_files_list_contains_examples(client):
    response = client.get("/api/ide/files")

    assert response.status_code == 200
    files = response.json()["files"]
    assert any(f == "api/test_example_api_patterns.py" for f in files)
    assert all(not f.startswith("/") for f in files)


def test_file_roundtrip(client, tmp_solution):
    saved = client.put("/api/ide/file", json={"path": tmp_solution, "content": "# updated\n"})
    read_back = client.get("/api/ide/file", params={"path": tmp_solution})

    assert saved.status_code == 200
    assert read_back.status_code == 200
    assert read_back.json()["content"] == "# updated\n"


def test_traversal_is_rejected(client):
    for evil in ("../backend/app/main.py", "api/../../secrets.py", "/etc/passwd"):
        response = client.get("/api/ide/file", params={"path": evil})
        assert response.status_code == 400, evil


def test_only_test_py_allowed(client):
    response = client.put(
        "/api/ide/file",
        json={"path": "api/helper.py", "content": "x = 1\n"},
    )

    assert response.status_code == 400


def test_run_executes_solution(client, tmp_solution):
    response = client.post("/api/ide/run", json={"path": tmp_solution})

    body = response.json()
    assert response.status_code == 200
    assert body["exit_code"] == 0, body["output"]
    assert "passed" in body["output"]


def test_locators_on_login_page(client):
    response = client.get("/api/ide/locators", params={"url": "/login"})

    body = response.json()
    assert response.status_code == 200
    ids = {item["testid"] for item in body["locators"]}
    assert {"email-input", "password-input", "login-button"} <= ids
    first = body["locators"][0]
    assert first["selector"].startswith("page.get_by_test_id(")


def test_locators_rejects_external_url(client):
    response = client.get("/api/ide/locators", params={"url": "https://example.com"})

    assert response.status_code == 400


def test_ide_page_requires_login(client):
    response = client.get("/ide")

    # Неавторизованный запрос уводит на страницу входа (TestClient следует
    # редиректам автоматически, поэтому проверяем конечный путь).
    assert response.url.path == "/login"
