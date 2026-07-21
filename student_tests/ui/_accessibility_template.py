"""Скопируйте как test_accessibility_<page>.py и выберите свою страницу."""
import json

import allure
import pytest


@pytest.mark.ui
def test_page_has_no_automatic_accessibility_violations(page, base_url, axe):
    page.goto(f"{base_url}/login")
    results = axe.run(page)
    allure.attach(
        json.dumps(results.response, ensure_ascii=False, indent=2),
        "axe-results.json",
        allure.attachment_type.JSON,
    )
    assert results.violations_count == 0
