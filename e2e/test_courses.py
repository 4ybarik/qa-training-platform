"""E2E: каталог курсов — поиск, фильтрация, переключение вида, запись."""
from playwright.sync_api import expect


def test_search_courses(login, base_url):
    page = login()
    page.goto(f"{base_url}/courses")
    page.get_by_test_id("search-input").fill("Playwright")
    page.get_by_test_id("apply-filters-button").click()
    expect(page.get_by_test_id("course-table")).to_be_visible()


def test_switch_to_cards_view(login, base_url):
    page = login()
    page.goto(f"{base_url}/courses")
    page.get_by_test_id("view-cards-button").click()
    expect(page.get_by_test_id("course-cards")).to_be_visible()
    expect(page.get_by_test_id("course-table")).to_be_hidden()


def test_pagination_next(login, base_url):
    page = login()
    page.goto(f"{base_url}/courses")
    page.get_by_test_id("page-next").click()
    expect(page.get_by_test_id("page-current")).to_contain_text("Стр. 2")


def test_enroll_in_course(login, base_url):
    page = login()
    page.goto(f"{base_url}/courses/1")
    badge = page.get_by_test_id("enrolled-badge")
    if badge.count() == 0:
        page.get_by_test_id("enroll-button").click()
    expect(page.get_by_test_id("enrolled-badge")).to_be_visible()
