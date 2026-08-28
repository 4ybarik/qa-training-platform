"""E2E-проверки ленты событий на дашборде."""


def test_event_feed_scrolls_without_growing_page(login):
    page = login()
    feed = page.get_by_test_id("ws-feed")
    before_page_height = page.evaluate("document.documentElement.scrollHeight")

    feed.evaluate(
        """element => {
            element.replaceChildren();
            for (let index = 0; index < 100; index += 1) {
                const item = document.createElement('li');
                item.textContent = `Событие ${index}`;
                element.appendChild(item);
            }
        }"""
    )

    metrics = feed.evaluate(
        """element => ({
            clientHeight: element.clientHeight,
            scrollHeight: element.scrollHeight,
            overflowY: getComputedStyle(element).overflowY,
            tabIndex: element.tabIndex,
        })"""
    )
    after_page_height = page.evaluate("document.documentElement.scrollHeight")

    assert metrics["overflowY"] == "auto"
    assert metrics["scrollHeight"] > metrics["clientHeight"]
    assert metrics["tabIndex"] == 0
    assert after_page_height == before_page_height
