"""Минимальный smoke-тест подтверждает связь IDE/Jenkins с приложением."""
import pytest


@pytest.mark.api
def test_health_contract(api_client):
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["status"] == "ok"
