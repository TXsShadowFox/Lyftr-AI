"""Secret exposure, error hygiene, CORS and injection resistance."""

from __future__ import annotations

import logging
from urllib.parse import quote

from tests.helpers import db_rows, get_messages, post_chat


def test_api_keys_never_appear_in_any_response(client, settings):
    secret_one, secret_two = settings.api_keys

    success = post_chat(client, "s-secret", "hello")
    cache_hit = post_chat(client, "s-secret-cache", "hello")
    failure = post_chat(
        client,
        "s-secret-fail",
        "hello",
        headers={"X-Simulate-Failure": "*=429"},
    )
    history = get_messages(client, "s-secret")
    health = client.get("/health")

    for response in (success, cache_hit, failure, history, health):
        assert secret_one not in response.text
        assert secret_two not in response.text

    assert success.status_code == 200
    assert cache_hit.json()["metadata"]["resolution_source"] == "LLM_CACHE"


def test_api_keys_never_appear_in_logs(client, settings, caplog):
    caplog.set_level(logging.INFO)

    post_chat(client, "s-log", "hello")
    post_chat(
        client,
        "s-log-fail",
        "hello",
        headers={"X-Simulate-Failure": "*=429"},
    )

    for key in settings.api_keys:
        assert key not in caplog.text
    assert "llm_live_success" in caplog.text or "llm_cache_hit" in caplog.text


def test_api_keys_are_not_persisted_in_sqlite(client, settings):
    post_chat(client, "s-db-secret", "hello")
    rows = db_rows(settings.database_url)

    for row in rows:
        for key in settings.api_keys:
            assert key not in row["content"]
            assert key not in (row["metadata"] or "")


def test_503_does_not_leak_provider_details(client):
    response = post_chat(
        client,
        "s-leak",
        "hello",
        headers={"X-Simulate-Failure": "*=500"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "all providers unavailable"}
    lowered = response.text.lower()
    for forbidden in ("traceback", "mock_provider_error", "simulated provider failure", "api_key"):
        assert forbidden not in lowered


def test_validation_errors_do_not_leak_internals(client):
    response = client.post("/chat", json={"session_id": "", "message": ""})

    assert response.status_code == 422
    lowered = response.text.lower()
    assert "traceback" not in lowered
    assert "test-key" not in lowered


def test_cors_allows_configured_origin(client):
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_rejects_unconfigured_origin(client):
    response = client.get("/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_allows_chat_headers(client):
    response = client.options(
        "/chat",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-simulate-failure",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "x-simulate-failure" in response.headers["access-control-allow-headers"].lower()


def test_session_id_is_parameterized_against_injection(client):
    injected = "' OR 1=1; DROP TABLE messages; --"
    response = get_messages(client, quote(injected, safe=""))

    assert response.status_code == 404
    assert response.json() == {"detail": "session not found"}

    # The table still exists and normal requests still work.
    assert post_chat(client, "s-after-injection", "hello").status_code == 200
    assert get_messages(client, "s-after-injection").status_code == 200
