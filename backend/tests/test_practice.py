"""Эталонные проверки каталога и детерминированных тестовых мишеней."""
import hashlib
import uuid


def headers() -> dict[str, str]:
    return {"X-Test-Run-Id": f"reference-{uuid.uuid4().hex}"}


def test_practice_catalog_is_task_only_and_bilingual(client):
    ru = client.get("/api/practice/catalog").json()
    en = client.get("/api/practice/catalog", params={"language": "en"}).json()

    assert ru["total"] == en["total"] == 48
    challenge = ru["tracks"][0]["challenges"][0]
    assert set(challenge) == {
        "slug", "track", "difficulty", "title", "task", "target",
        "test_path", "criteria", "markers",
    }
    assert "theory" not in challenge
    assert ru["tracks"][0]["title"] != en["tracks"][0]["title"]


def test_practice_catalog_unknown_challenge(client):
    assert client.get("/api/practice/catalog/not-found").status_code == 404


def test_controlled_mutations_are_opt_in_and_observable(client):
    catalog = client.get("/api/practice/mutations")
    assert catalog.status_code == 200
    assert catalog.json()["total"] >= 10

    normal = client.get("/health")
    mutated = client.get("/health", headers={"X-Test-Mutation": "health-status"})
    unknown = client.get("/health", headers={"X-Test-Mutation": "not-registered"})

    assert normal.json()["status"] == "ok"
    assert mutated.json()["status"] == "degraded"
    assert unknown.json()["status"] == "ok"


def test_echo_status_and_schema_targets(client):
    echo = client.post(
        "/api/practice/echo?q=Привет",
        headers={"X-Echo": "correlation"},
        json={"message": "test", "extra": 42},
    )
    assert echo.status_code == 200
    assert echo.json()["body"] == {"message": "test", "extra": 42}
    assert echo.json()["query"] == {"q": "Привет"}
    assert echo.json()["x_echo"] == "correlation"

    assert client.get("/api/practice/status/204").content == b""
    assert client.get("/api/practice/status/503").status_code == 503
    assert client.get("/api/practice/status/418").status_code == 422
    assert client.get("/api/practice/schema/stable").json()["id"] == 101
    assert client.get("/api/practice/schema/wrong-type").json()["id"] == "101"


def test_deterministic_rate_limit_and_reset(client):
    run_headers = headers()
    for expected_remaining in (2, 1, 0):
        response = client.get(
            "/api/practice/rate-limit", headers=run_headers, params={"limit": 3}
        )
        assert response.status_code == 200
        assert response.headers["ratelimit-remaining"] == str(expected_remaining)

    limited = client.get("/api/practice/rate-limit", headers=run_headers, params={"limit": 3})
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "1"

    assert client.delete("/api/practice/state", headers=run_headers).status_code == 204
    reset = client.get("/api/practice/rate-limit", headers=run_headers, params={"limit": 3})
    assert reset.status_code == 200
    assert reset.json()["attempt"] == 1


def test_practice_echo_cors_preflight(client):
    response = client.options(
        "/api/practice/echo",
        headers={
            "Origin": "https://tests.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-echo",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://tests.example"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert response.headers["access-control-allow-credentials"] == "true"


def test_resource_crud_idempotency_and_etag(client):
    run_headers = headers()
    payload = {"name": "Alpha", "quantity": 2, "price": 10.5, "tags": ["api"]}

    missing_namespace = client.post("/api/practice/resources", json=payload)
    assert missing_namespace.status_code == 400

    created = client.post(
        "/api/practice/resources",
        headers={**run_headers, "Idempotency-Key": "create-alpha"},
        json=payload,
    )
    assert created.status_code == 201
    assert created.headers["etag"] == '"1"'
    item_id = created.json()["id"]

    replayed = client.post(
        "/api/practice/resources",
        headers={**run_headers, "Idempotency-Key": "create-alpha"},
        json=payload,
    )
    assert replayed.status_code == 200
    assert replayed.headers["idempotent-replayed"] == "true"
    assert replayed.json()["id"] == item_id
    conflict = client.post(
        "/api/practice/resources",
        headers={**run_headers, "Idempotency-Key": "create-alpha"},
        json={**payload, "name": "Different payload"},
    )
    assert conflict.status_code == 409

    listed = client.get("/api/practice/resources", headers=run_headers).json()
    assert listed["total"] == 1
    assert listed["items"][0]["name"] == "Alpha"

    without_version = client.put(
        f"/api/practice/resources/{item_id}", headers=run_headers, json=payload
    )
    assert without_version.status_code == 428
    stale = client.put(
        f"/api/practice/resources/{item_id}",
        headers={**run_headers, "If-Match": '"0"'},
        json=payload,
    )
    assert stale.status_code == 412

    updated = client.put(
        f"/api/practice/resources/{item_id}",
        headers={**run_headers, "If-Match": '"1"'},
        json={**payload, "name": "Beta"},
    )
    assert updated.status_code == 200
    assert updated.headers["etag"] == '"2"'

    assert client.delete(f"/api/practice/resources/{item_id}", headers=run_headers).status_code == 204
    assert client.get(f"/api/practice/resources/{item_id}", headers=run_headers).status_code == 404


def test_resource_pagination_search_sort_and_cleanup(client):
    run_headers = headers()
    for name in ("gamma", "Alpha", "beta"):
        response = client.post(
            "/api/practice/resources", headers=run_headers, json={"name": name}
        )
        assert response.status_code == 201

    page = client.get(
        "/api/practice/resources",
        headers=run_headers,
        params={"page": 1, "size": 2, "sort": "name"},
    ).json()
    assert [item["name"] for item in page["items"]] == ["Alpha", "beta"]
    assert page["total"] == 3

    searched = client.get(
        "/api/practice/resources", headers=run_headers, params={"search": "AMM"}
    ).json()
    assert [item["name"] for item in searched["items"]] == ["gamma"]
    assert client.delete("/api/practice/resources", headers=run_headers).status_code == 204


def test_async_job_completed_and_failed(client):
    for outcome, expected in (("completed", "COMPLETED"), ("failed", "FAILED")):
        run_headers = headers()
        created = client.post(
            "/api/practice/jobs",
            headers=run_headers,
            json={"polls_to_complete": 2, "outcome": outcome},
        )
        assert created.status_code == 202
        location = created.headers["location"]
        assert client.get(location, headers=run_headers).json()["status"] == "PENDING"
        final = client.get(location, headers=run_headers).json()
        assert final["status"] == expected


def test_namespace_cleanup_removes_all_temporary_state(client):
    run_headers = headers()
    resource = client.post(
        "/api/practice/resources", headers=run_headers, json={"name": "cleanup"}
    )
    job = client.post("/api/practice/jobs", headers=run_headers, json={})
    file_response = client.post(
        "/api/practice/files",
        headers=run_headers,
        files={"file": ("cleanup.txt", b"cleanup", "text/plain")},
    )
    webhook = client.post("/api/practice/webhooks", headers=run_headers, json={"cleanup": True})
    assert (
        resource.status_code,
        job.status_code,
        file_response.status_code,
        webhook.status_code,
    ) == (201, 202, 201, 202)

    assert client.delete("/api/practice/state", headers=run_headers).status_code == 204
    assert client.get("/api/practice/resources", headers=run_headers).json()["total"] == 0
    assert client.get(job.headers["location"], headers=run_headers).status_code == 404
    assert client.get(
        f"/api/practice/files/{file_response.json()['id']}", headers=run_headers
    ).status_code == 404
    assert client.get("/api/practice/webhooks", headers=run_headers).json()["total"] == 0


def test_file_roundtrip(client):
    run_headers = headers()
    content = b"deterministic practice file\n"
    uploaded = client.post(
        "/api/practice/files",
        headers=run_headers,
        files={"file": ("fixture.txt", content, "text/plain")},
    )
    assert uploaded.status_code == 201
    body = uploaded.json()
    assert body["sha256"] == hashlib.sha256(content).hexdigest()
    assert body["size"] == len(content)

    downloaded = client.get(f"/api/practice/files/{body['id']}", headers=run_headers)
    assert downloaded.content == content
    assert 'filename="fixture.txt"' in downloaded.headers["content-disposition"]

    empty = client.post(
        "/api/practice/files",
        headers=run_headers,
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert empty.status_code == 422


def test_redirect_cookie_and_webhook_targets(client):
    direct = client.get("/api/practice/redirect/2", follow_redirects=False)
    assert direct.status_code == 302
    followed = client.get("/api/practice/redirect/2", follow_redirects=True)
    assert followed.json()["status"] == "arrived"
    assert len(followed.history) == 2

    assert client.post("/api/practice/cookies/set", params={"value": "abc"}).status_code == 200
    assert client.get("/api/practice/cookies/read").json()["value"] == "abc"
    assert client.delete("/api/practice/cookies").status_code == 200
    assert client.get("/api/practice/cookies/read").json()["value"] is None

    run_headers = headers()
    for value in (1, 2):
        accepted = client.post(
            "/api/practice/webhooks",
            headers={**run_headers, "X-Correlation-Id": f"event-{value}"},
            json={"value": value},
        )
        assert accepted.status_code == 202
    events = client.get("/api/practice/webhooks", headers=run_headers).json()
    assert [item["sequence"] for item in events["items"]] == [1, 2]
    assert client.delete("/api/practice/webhooks", headers=run_headers).status_code == 204


def test_practice_web_requires_login_and_renders_catalog(client):
    assert client.get("/practice", follow_redirects=False).status_code == 303

    login = client.post(
        "/web/login",
        data={"email": "user@test.com", "password": "Password123!"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    catalog = client.get("/practice")
    details = client.get("/practice/challenges/echo-contract")
    components = client.get("/practice/components")

    assert catalog.status_code == details.status_code == components.status_code == 200
    assert 'data-testid="practice-title"' in catalog.text
    assert "student_tests/api/test_echo_contract.py" in details.text
    assert 'data-testid="practice-shadow"' in components.text
    learning = client.get("/learning", follow_redirects=False)
    lesson = client.get("/learning/echo-contract")
    assert learning.status_code == lesson.status_code == 200
    assert 'data-testid="learning-hero"' in learning.text
    assert 'data-testid="learning-start"' in lesson.text
