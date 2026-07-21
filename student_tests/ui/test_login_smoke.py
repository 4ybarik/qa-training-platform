"""Минимальный UI smoke; остальные задачи ученик добавляет рядом."""
import re

import pytest
from playwright.sync_api import expect


@pytest.mark.ui
def test_user_can_open_practice_catalog(login):
    page = login()
    page.get_by_test_id("nav-practice").click()

    expect(page).to_have_url(re.compile(r"/practice$"))
    expect(page.get_by_test_id("practice-title")).to_be_visible()
