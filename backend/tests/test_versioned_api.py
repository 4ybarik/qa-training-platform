def test_v1_is_deprecated_but_keeps_legacy_contract(client):
    response = client.get("/api/v1/courses", params={"page": 1, "size": 2})

    assert response.status_code == 200
    assert response.headers["deprecation"] == "true"
    assert response.headers["sunset"]
    assert 'rel="successor-version"' in response.headers["link"]
    body = response.json()
    assert body["version"] == "v1"
    assert len(body["items"]) == 2
    assert set(body["items"][0]) == {"id", "title", "price", "status"}


def test_v2_exposes_explicit_money_and_pagination_contract(client):
    response = client.get("/api/v2/courses", params={"page": 1, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v2"
    assert len(body["data"]) == 2
    assert set(body["data"][0]) == {"id", "name", "pricing", "lifecycle"}
    assert body["data"][0]["pricing"]["currency"] == "RUB"
    assert body["pagination"]["page_size"] == 2
