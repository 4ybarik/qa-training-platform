"""E2E: каталог задач и UI-мишени полигона."""
from playwright.sync_api import expect


def test_practice_catalog_opens_task(login):
    page = login()
    page.get_by_test_id("nav-practice").click()
    expect(page.get_by_test_id("practice-title")).to_be_visible()

    page.get_by_test_id("open-challenge-echo-contract").click()
    expect(page.get_by_test_id("challenge-title")).to_contain_text("Контракт")
    expect(page.get_by_test_id("challenge-test-path")).to_contain_text("student_tests/api")


def test_practice_catalog_switches_to_english(login, base_url):
    page = login()
    page.goto(f"{base_url}/practice")
    page.get_by_test_id("language-en").click()

    expect(page.get_by_test_id("practice-title")).to_have_text("Test automation practice catalog")
    expect(page.get_by_test_id("nav-practice")).to_have_text("Practice tasks")


def test_ui_target_form_dynamic_iframe_shadow_and_tab(login, base_url):
    page = login()
    page.goto(f"{base_url}/practice/components")

    page.get_by_label("Full name").fill("Анна Automation")
    page.get_by_label("Plan").select_option("Pro")
    page.get_by_test_id("practice-updates").check()
    page.get_by_role("button", name="Save form").click()
    expect(page.get_by_test_id("practice-form-result")).to_contain_text("Анна Automation")

    page.get_by_test_id("spawn-dynamic").click()
    expect(page.get_by_test_id("dynamic-element")).to_be_visible(timeout=3_000)

    frame = page.frame_locator('[data-testid="practice-iframe"]')
    frame.get_by_label("Frame value").fill("inside")
    frame.get_by_test_id("iframe-button").click()
    expect(frame.get_by_test_id("iframe-button")).to_have_text("Frame saved")

    shadow = page.get_by_test_id("practice-shadow")
    shadow.get_by_label("Shadow value").fill("shadow data")
    shadow.get_by_role("button", name="Save shadow").click()
    expect(shadow.locator("output")).to_have_text("shadow data")

    with page.expect_popup() as popup_info:
        page.get_by_test_id("open-new-tab").click()
    popup = popup_info.value
    expect(popup.get_by_test_id("new-tab-status")).to_have_text("ready")
    popup.close()
