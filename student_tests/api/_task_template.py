"""Скопируйте файл как test_<task>.py; исходный шаблон pytest не собирает."""
import pytest


@pytest.mark.api
def test_api_task(api_client, run_headers):
    response = api_client.get("/api/practice/resources", headers=run_headers)

    assert response.status_code == 200
    assert response.json()["items"] == []
