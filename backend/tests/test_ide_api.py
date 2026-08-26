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


def test_create_new_file_and_run(client, tmp_solution):
    created = client.post(
        "/api/ide/files",
        json={"path": "ui/test_tmp_ide_created.py", "content": "def test_ok():\n    assert True\n"},
    )

    assert created.status_code == 200
    assert (STUDENT_DIR / "ui/test_tmp_ide_created.py").is_file()


def test_create_duplicate_conflicts(client):
    first = client.post(
        "/api/ide/files",
        json={"path": "api/test_tmp_ide_dup.py", "content": "x = 1\n"},
    )
    second = client.post(
        "/api/ide/files",
        json={"path": "api/test_tmp_ide_dup.py", "content": "x = 2\n"},
    )

    assert first.status_code == 200
    assert second.status_code == 409


@pytest.fixture(autouse=True)
def _cleanup_tmp_files():
    yield
    for name in ("ui/test_tmp_ide_created.py", "api/test_tmp_ide_dup.py"):
        (STUDENT_DIR / name).unlink(missing_ok=True)


def test_create_rejects_unknown_dir(client):
    response = client.post(
        "/api/ide/files",
        json={"path": "hacks/test_evil.py", "content": ""},
    )

    assert response.status_code == 400


def test_delete_file(client, tmp_solution):
    deleted = client.delete("/api/ide/file", params={"path": tmp_solution})
    still_there = client.get("/api/ide/file", params={"path": tmp_solution})

    assert deleted.status_code == 200
    assert deleted.json()["deleted"] == tmp_solution
    assert still_there.status_code == 404
    assert not (STUDENT_DIR / tmp_solution).exists()


def test_delete_missing_returns_404(client):
    response = client.delete("/api/ide/file", params={"path": "api/test_never_created.py"})

    assert response.status_code == 404


def test_delete_rejects_bad_paths(client):
    for evil in ("../backend/app/main.py", "api/helper.py"):
        response = client.delete("/api/ide/file", params={"path": evil})
        assert response.status_code == 400, evil


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
