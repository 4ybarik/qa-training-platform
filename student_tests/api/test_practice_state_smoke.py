"""Smoke изоляции: подтверждает доступность stateful practice API и teardown."""
import pytest


@pytest.mark.api
def test_isolated_practice_namespace_starts_empty(api_client, run_headers):
    response = api_client.get("/api/practice/resources", headers=run_headers)

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": 10}
