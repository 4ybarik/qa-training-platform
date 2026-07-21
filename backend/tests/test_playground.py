"""Воспроизводимые сценарии Testing Playground и контроль доступа."""

import uuid

from tests.conftest import auth


def test_global_playground_configuration_requires_admin(client, user_token):
    response = client.put(
        "/api/playground",
        headers=auth(user_token),
        json={"enabled": False, "latency_ms": 0, "error_rate": 0},
    )
    assert response.status_code == 403


def test_playground_configuration_is_validated(client, admin_token):
    response = client.put(
        "/api/playground",
        headers=auth(admin_token),
        json={"enabled": False, "latency_ms": 5001, "error_rate": 0},
    )
    assert response.status_code == 422


def test_deterministic_failure_scenario(client):
    response = client.get(
        "/api/courses",
        headers={"X-Playground-Scenario": "fail", "X-Playground-Latency-Ms": "0"},
    )
    assert response.status_code == 500
    assert response.json()["detail"].startswith("Testing Playground")


def test_fail_first_is_isolated_by_run_id(client):
    run_id = uuid.uuid4().hex
    headers = {
        "X-Playground-Scenario": "fail-first",
        "X-Playground-Run": run_id,
        "X-Playground-Latency-Ms": "0",
    }

    assert client.get("/api/courses", headers=headers).status_code == 503
    assert client.get("/api/courses", headers=headers).status_code == 200


def test_fail_first_requires_run_id(client):
    response = client.get(
        "/api/courses",
        headers={"X-Playground-Scenario": "fail-first", "X-Playground-Latency-Ms": "0"},
    )
    assert response.status_code == 400


def test_malformed_json_scenario(client):
    response = client.get(
        "/api/courses",
        headers={"X-Playground-Scenario": "malformed-json", "X-Playground-Latency-Ms": "0"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.text == '{"detail": "truncated"'
