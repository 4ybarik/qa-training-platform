"""E2E: прохождение экзамена со всеми типами вопросов."""
from playwright.sync_api import expect


def test_take_exam(login, base_url):
    page = login()
    page.goto(f"{base_url}/exams/1")
    expect(page.get_by_test_id("exam-title")).to_be_visible()
    expect(page.get_by_test_id("countdown-timer")).to_be_visible()

    # Отвечаем на первый вопрос (одиночный выбор) — берём первый radio.
    first_question = page.get_by_test_id("question-1")
    first_question.locator('input[type="radio"]').first.check()

    page.get_by_test_id("exam-submit-button").click()
    expect(page.get_by_test_id("exam-result")).to_be_visible()
    expect(page.get_by_test_id("exam-score")).to_be_visible()


def test_exam_retake_available(login, base_url):
    page = login()
    page.goto(f"{base_url}/exams/1")
    page.get_by_test_id("exam-submit-button").click()
    expect(page.get_by_test_id("retake-button")).to_be_visible()
