"""GET /health contract."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok_with_two_keys_and_cache(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "keys_configured": 2,
        "cache_enabled": True,
    }
    assert set(response.json()) == {"status", "keys_configured", "cache_enabled"}


def test_health_reports_actual_key_count(make_settings):
    settings = make_settings(llm_api_keys="alpha,beta,gamma")
    with TestClient(create_app(settings)) as client:
        body = client.get("/health").json()

    assert body["status"] == "ok"
    assert body["keys_configured"] == 3


def test_health_fails_with_fewer_than_two_keys(make_settings):
    settings = make_settings(llm_api_keys="only-one")
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["keys_configured"] == 1
    assert body["cache_enabled"] is True
    assert "at least two API keys" in body["detail"]


def test_health_fails_when_cache_is_disabled(make_settings):
    settings = make_settings(cache_enabled=False)
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["keys_configured"] == 2
    assert body["cache_enabled"] is False
    assert "cache disabled" in body["detail"]
