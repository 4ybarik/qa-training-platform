import pytest


@pytest.mark.integration
def test_external_service_success_and_error_mapping(api_client):
    success = api_client.get("/api/integrations/external/profiles/42")
    missing = api_client.get("/api/integrations/external/profiles/404")
    failed = api_client.get("/api/integrations/external/profiles/error")

    assert success.status_code == 200
    assert success.json()["profile"]["tier"] == "gold"
    assert missing.status_code == 404
    assert failed.status_code == 502
