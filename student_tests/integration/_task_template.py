"""Шаблон интеграционного теста; копия должна называться test_<task>.py."""
import pytest


@pytest.mark.integration
def test_integration_task(api_client, run_headers):
    response = api_client.post(
        "/api/practice/jobs",
        headers=run_headers,
        json={"polls_to_complete": 2, "outcome": "completed"},
    )

    assert response.status_code == 202
    assert response.headers["location"].startswith("/api/practice/jobs/")
