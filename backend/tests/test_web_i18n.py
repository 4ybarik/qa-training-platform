"""Проверки локализации серверного веб-интерфейса."""

import re
from pathlib import Path

from app.web.i18n import JAVASCRIPT_KEYS, TRANSLATIONS


APP_DIR = Path(__file__).resolve().parents[1] / "app"


def test_translation_catalogs_have_the_same_keys():
    assert TRANSLATIONS["ru"].keys() == TRANSLATIONS["en"].keys()
    assert set(JAVASCRIPT_KEYS) <= TRANSLATIONS["ru"].keys()


def test_all_ui_translation_keys_exist():
    template_keys: set[str] = set()
    for template in (APP_DIR / "templates").glob("*.html"):
        template_keys.update(re.findall(r"\bt\('([^']+)'", template.read_text()))

    javascript_keys = set(
        re.findall(
            r'\b(?:QATP\.)?t\("([^"]+)"',
            (APP_DIR / "static" / "js" / "app.js").read_text(),
        )
    )
    javascript_keys.update(
        re.findall(
            r'\bQATP\.t\("([^"]+)"',
            (APP_DIR / "templates" / "exam_form.html").read_text(),
        )
    )

    assert template_keys <= TRANSLATIONS["ru"].keys()
    assert javascript_keys <= set(JAVASCRIPT_KEYS)


def test_russian_is_the_default_ui_language(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert '<html lang="ru">' in response.text
    assert "Вход в систему" in response.text
    assert 'data-testid="language-ru"' in response.text
    assert 'data-testid="language-en"' in response.text
    assert 'class="language-option active"' in response.text
    assert 'data-testid="language-select"' not in response.text
    assert "Применить язык" not in response.text


def test_language_switch_is_saved_in_cookie(client):
    response = client.post(
        "/web/language",
        data={"language": "en", "next_url": "/login"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert response.cookies["language"] == "en"

    page = client.get("/login")
    assert '<html lang="en">' in page.text
    assert "Remember me" in page.text
    assert "Forgot your password?" in page.text
    assert 'data-testid="language-en"' in page.text
    assert 'value="en"' in page.text
    assert '"network_error": "Network error"' in page.text

    reset_page = client.get("/forgot-password")
    assert reset_page.status_code == 200
    assert "Reset password" in reset_page.text


def test_language_switch_rejects_external_redirect(client):
    for unsafe_target in ("https://example.org/phishing", r"/\example.org/phishing"):
        response = client.post(
            "/web/language",
            data={"language": "en", "next_url": unsafe_target},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/"


def test_unknown_language_falls_back_to_russian(client):
    response = client.post(
        "/web/language",
        data={"language": "de", "next_url": "/login"},
        follow_redirects=False,
    )

    assert response.cookies["language"] == "ru"


def test_authenticated_pages_render_in_english(client):
    client.post(
        "/web/language",
        data={"language": "en", "next_url": "/login"},
        follow_redirects=False,
    )
    login = client.post(
        "/web/login",
        data={"email": "admin@test.com", "password": "Password123!"},
        follow_redirects=False,
    )
    assert login.status_code == 303

    expected_text_by_path = {
        "/dashboard": "Courses in catalog",
        "/practice": "Test automation practice catalog",
        "/practice/challenges/echo-contract": "Echo request contract",
        "/practice/components": "deterministic target page",
        "/courses": "All categories",
        "/courses/new": "New course",
        "/courses/1": "Back to catalog",
        "/courses/1/exams/new": "New exam",
        "/exams/1": "Finish exam",
        "/profile": "Skills (multiple selection)",
        "/notifications": "Unread",
        "/admin": "Users and roles",
        "/playground": "Enable chaos",
    }

    for path, expected_text in expected_text_by_path.items():
        response = client.get(path)
        assert response.status_code == 200, path
        assert '<html lang="en">' in response.text, path
        assert expected_text in response.text, path
