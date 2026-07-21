import pytest


@pytest.mark.integration
def test_disposable_user_can_authenticate(user_factory, auth_headers, api_client):
    user = user_factory(role="USER")

    response = api_client.get("/api/auth/me", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json()["email"] == user["email"]
