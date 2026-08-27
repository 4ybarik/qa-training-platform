"""Веб-профиль: безопасная загрузка и валидация аватара."""
from pathlib import Path

from tests.conftest import auth
from app.web.router import AVATAR_DIR


def test_png_avatar_is_saved_and_exposed_in_profile(client, user_token):
    response = client.post(
        "/web/profile",
        headers=auth(user_token),
        data={"phone": "+7 900 000-00-00", "address": "Test", "skills": "API"},
        files={
            "avatar": (
                "avatar.png",
                b"\x89PNG\r\n\x1a\n" + b"test-image-data",
                "image/png",
            )
        },
    )

    assert response.status_code == 200
    profile = client.get("/api/profile", headers=auth(user_token)).json()
    assert profile["avatar_url"].startswith("/static/uploads/avatars/user-")
    created = AVATAR_DIR / Path(profile["avatar_url"]).name
    try:
        assert created.exists()
        assert 'data-testid="avatar-preview"' in response.text
    finally:
        created.unlink(missing_ok=True)


def test_avatar_rejects_mime_spoofing(client, user_token):
    response = client.post(
        "/web/profile",
        headers=auth(user_token),
        data={"phone": "unchanged", "address": "", "skills": "API"},
        files={"avatar": ("fake.png", b"<script>alert(1)</script>", "image/png")},
    )

    assert response.status_code == 400
    assert 'data-testid="profile-error"' in response.text
    assert client.get("/api/profile", headers=auth(user_token)).json()["phone"] is None
