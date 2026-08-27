import time
from threading import Event

import pytest


@pytest.mark.integration
def test_redis_cache_roundtrip(api_client, integration_headers):
    stored = api_client.put(
        "/api/integrations/cache/example",
        headers=integration_headers,
        json={"value": {"answer": 42}, "ttl_seconds": 30},
    )
    loaded = api_client.get("/api/integrations/cache/example", headers=integration_headers)

    assert stored.status_code == 200
    assert loaded.status_code == 200
    assert loaded.json()["value"] == {"answer": 42}


@pytest.mark.integration
def test_real_queue_worker_processes_job(api_client, integration_headers):
    created = api_client.post(
        "/api/integrations/jobs",
        headers=integration_headers,
        json={"payload": {"values": [1, 2, 3]}, "delay_ms": 50},
    )
    assert created.status_code == 202

    deadline = time.monotonic() + 5
    state = None
    while time.monotonic() < deadline:
        state = api_client.get(created.json()["location"], headers=integration_headers)
        assert state.status_code == 200
        if state.json()["status"] in {"FINISHED", "FAILED"}:
            break
        # Ограниченное ожидание не нагружает Redis и завершится по deadline.
        Event().wait(0.1)

    assert state is not None
    assert state.json()["status"] == "FINISHED"
    assert state.json()["result"]["sum"] == 6
