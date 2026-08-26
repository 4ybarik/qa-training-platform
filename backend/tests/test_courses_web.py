"""Web enroll: domain errors must surface to the user."""
import uuid

from tests.conftest import auth


def test_web_enroll_duplicate_shows_error(client):
    email = f"web_enr_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    token = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123!"},
    ).json()["access_token"]
    headers = auth(token)

    assert client.post("/api/courses/1/enroll", headers=headers).status_code == 200

    response = client.post(
        "/web/courses/1/enroll",
        headers=headers,
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "enroll_error=" in response.headers["location"]

    page = client.get(response.headers["location"], headers=headers)
    assert page.status_code == 200
    assert 'data-testid="enroll-error"' in page.text
