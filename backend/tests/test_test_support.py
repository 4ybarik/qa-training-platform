from app.core.config import get_settings


def _headers(run_id: str) -> dict[str, str]:
    return {
        "X-Test-Run-Id": run_id,
        "X-Test-Support-Key": get_settings().test_support_key,
    }


def test_test_support_requires_key(client):
    response = client.post(
        "/api/test-support/users",
        headers={"X-Test-Run-Id": "pytest-no-key"},
        json={},
    )
    assert response.status_code == 403


def test_test_support_creates_and_cleans_isolated_entities(client):
    first_headers = _headers("pytest-test-data-first")
    second_headers = _headers("pytest-test-data-second")

    first = client.post(
        "/api/test-support/users",
        headers=first_headers,
        json={"role": "MANAGER"},
    )
    second = client.post(
        "/api/test-support/users",
        headers=second_headers,
        json={},
    )
    course = client.post(
        "/api/test-support/courses",
        headers=first_headers,
        json={"title": "Isolated course", "status": "DRAFT"},
    )

    assert first.status_code == second.status_code == course.status_code == 201
    assert first.json()["email"] != second.json()["email"]
    assert first.json()["role"] == "MANAGER"

    cleanup = client.delete("/api/test-support/state", headers=first_headers)
    assert cleanup.status_code == 200
    assert cleanup.json()["removed"] == {"users": 1, "courses": 1}

    second_login = client.post(
        "/api/auth/login",
        json={"email": second.json()["email"], "password": second.json()["password"]},
    )
    assert second_login.status_code == 200
    client.delete("/api/test-support/state", headers=second_headers)
