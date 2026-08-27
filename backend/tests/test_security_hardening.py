"""Production guards, browser CSRF boundary and security headers."""
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_debug_wildcard_cors_and_local_runner():
    common = {
        "environment": "production",
        "secret_key": "a-production-secret-that-is-long-enough",
        "_env_file": None,
    }
    with pytest.raises(ValidationError, match="DEBUG"):
        Settings(**common)
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(**common, debug=False)
    with pytest.raises(ValidationError, match="IDE_ALLOW_LOCAL_RUNNER"):
        Settings(**common, debug=False, cors_origins=["https://training.example.com"])

    valid = Settings(
        **common,
        debug=False,
        cors_origins=["https://training.example.com"],
        ide_allow_local_runner=False,
    )
    assert valid.environment == "production"


def test_cookie_authenticated_cross_site_post_is_blocked(client):
    login = client.post(
        "/web/login",
        data={"email": "user@test.com", "password": "Password123!"},
        follow_redirects=False,
    )
    assert login.status_code == 303

    blocked = client.post(
        "/web/language",
        data={"language": "en", "next_url": "/dashboard"},
        headers={"Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"},
    )
    allowed = client.post(
        "/web/language",
        data={"language": "en", "next_url": "/dashboard"},
        headers={"Origin": "http://testserver", "Sec-Fetch-Site": "same-origin"},
        follow_redirects=False,
    )

    assert blocked.status_code == 403
    assert allowed.status_code == 303


def test_security_headers_are_present(client):
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
