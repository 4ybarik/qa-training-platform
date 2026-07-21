"""Шаблон UI-теста; копия должна называться test_<task>.py."""
import pytest
from playwright.sync_api import expect


@pytest.mark.ui
def test_ui_task(login, base_url):
    page = login()
    page.goto(f"{base_url}/practice/components")

    expect(page.get_by_test_id("components-title")).to_be_visible()
