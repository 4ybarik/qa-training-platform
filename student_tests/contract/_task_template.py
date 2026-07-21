"""Шаблон контрактного теста; копия должна называться test_<task>.py."""
import pytest


@pytest.mark.contract
def test_stable_schema(api_client):
    response = api_client.get("/api/practice/schema/stable")

    assert response.status_code == 200
    assert set(response.json()) == {"id", "name", "active", "metadata"}
