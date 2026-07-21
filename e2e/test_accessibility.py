import json

import allure
from axe_playwright_python.sync_playwright import Axe


def _assert_accessible(page, name: str):
    results = Axe().run(page)
    allure.attach(
        json.dumps(results.response, ensure_ascii=False, indent=2),
        f"axe-{name}.json",
        allure.attachment_type.JSON,
    )
    assert results.violations_count == 0, [
        {"id": item["id"], "impact": item.get("impact"), "help": item["help"]}
        for item in results.response["violations"]
    ]


def test_login_page_has_no_automatic_accessibility_violations(page, base_url):
    page.goto(f"{base_url}/login")
    _assert_accessible(page, "login")


def test_practice_components_have_no_automatic_accessibility_violations(login, base_url):
    page = login()
    page.goto(f"{base_url}/practice/components")
    _assert_accessible(page, "practice-components")
