"""Key failover, failure simulation and 503 behavior."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import db_message_count, get_messages, post_chat


def test_simulated_429_on_key_1_falls_back_to_key_2(client, provider, settings):
    response = post_chat(
        client,
        "s-429",
        "hello",
        headers={"X-Simulate-Failure": "key_1=429"},
    )

    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert response.json()["reply"] == "Echo: hello"
    assert metadata["key_id"] == "key_2"
    assert metadata["fallback_attempts"] == 1
    assert metadata["resolution_source"] == "LIVE_INFERENCE"
    # The failed key never reached the provider; the second key did.
    assert [call["key"] for call in provider.calls] == ["test-key-2"]
    assert db_message_count(settings.database_url) == 2


def test_simulated_500_on_key_1_falls_back_to_key_2(client, provider):
    response = post_chat(
        client,
        "s-500",
        "hello",
        headers={"X-Simulate-Failure": "key_1=500"},
    )

    assert response.status_code == 200
    assert response.json()["metadata"]["key_id"] == "key_2"
    assert response.json()["metadata"]["fallback_attempts"] == 1
    assert [call["key"] for call in provider.calls] == ["test-key-2"]


def test_all_keys_simulated_failure_returns_exact_503_and_saves_nothing(
    client, provider, settings
):
    response = post_chat(
        client,
        "s-all-fail",
        "hello",
        headers={"X-Simulate-Failure": "*=429"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "all providers unavailable"}
    assert response.headers["content-type"].startswith("application/json")
    assert provider.call_count == 0
    assert db_message_count(settings.database_url) == 0
    assert get_messages(client, "s-all-fail").status_code == 404


def test_real_provider_429_fails_over_to_next_key(client, provider):
    provider.failures["test-key-1"] = 429

    response = post_chat(client, "s-real-429", "hello")

    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert metadata["key_id"] == "key_2"
    assert metadata["fallback_attempts"] == 1
    assert [call["key"] for call in provider.calls] == ["test-key-1", "test-key-2"]


def test_real_provider_500_fails_over_to_next_key(client, provider):
    provider.failures["test-key-1"] = 500

    response = post_chat(client, "s-real-500", "hello")

    assert response.status_code == 200
    assert response.json()["metadata"]["key_id"] == "key_2"
    assert response.json()["metadata"]["fallback_attempts"] == 1


def test_real_provider_failure_of_entire_pool_returns_503(
    client, provider, settings
):
    provider.failures["test-key-1"] = 500
    provider.failures["test-key-2"] = 502

    response = post_chat(client, "s-pool-down", "hello")

    assert response.status_code == 503
    assert response.json() == {"detail": "all providers unavailable"}
    assert provider.call_count == 2
    assert db_message_count(settings.database_url) == 0


def test_three_keys_report_two_failed_attempts(make_settings, provider):
    settings = make_settings(llm_api_keys="alpha,beta,gamma")
    with TestClient(create_app(settings)) as client:
        response = post_chat(
            client,
            "s-three",
            "hello",
            headers={"X-Simulate-Failure": "key_1=429,key_2=500"},
        )

    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert metadata["key_id"] == "key_3"
    assert metadata["fallback_attempts"] == 2
    assert [call["key"] for call in provider.calls] == ["gamma"]


def test_failure_simulation_is_ignored_when_disabled(make_settings, provider):
    settings = make_settings(enable_failure_simulation=False)
    with TestClient(create_app(settings)) as client:
        response = post_chat(
            client,
            "s-sim-off",
            "hello",
            headers={"X-Simulate-Failure": "key_1=429"},
        )

    assert response.status_code == 200
    assert response.json()["metadata"]["key_id"] == "key_1"
    assert response.json()["metadata"]["fallback_attempts"] == 0


def test_simulation_only_affects_the_current_request(client, provider):
    first = post_chat(
        client,
        "s-scoped-a",
        "alpha",
        headers={"X-Simulate-Failure": "key_1=429"},
    )
    second = post_chat(client, "s-scoped-b", "beta")

    assert first.json()["metadata"]["key_id"] == "key_2"
    assert second.json()["metadata"]["key_id"] == "key_1"
    assert second.json()["metadata"]["fallback_attempts"] == 0


def test_malformed_or_unsupported_simulation_header_is_ignored(client, provider):
    response = post_chat(
        client,
        "s-malformed",
        "hello",
        headers={"X-Simulate-Failure": "garbage,key_1=418,key_9=429,=429"},
    )

    assert response.status_code == 200
    assert response.json()["metadata"]["key_id"] == "key_1"
    assert response.json()["metadata"]["fallback_attempts"] == 0


def test_failed_request_does_not_change_existing_history(client, provider, settings):
    assert post_chat(client, "s-existing", "alpha").status_code == 200
    before = db_message_count(settings.database_url)

    failed = post_chat(
        client,
        "s-existing",
        "beta",
        headers={"X-Simulate-Failure": "*=503"},
    )

    assert failed.status_code == 503
    assert db_message_count(settings.database_url) == before
    history = get_messages(client, "s-existing").json()
    assert [m["content"] for m in history["messages"]] == ["alpha", "Echo: alpha"]


def test_failed_request_does_not_write_cache(client, provider):
    failed = post_chat(
        client,
        "s-failed-cache",
        "What is the capital of France?",
        headers={"X-Simulate-Failure": "*=429"},
    )
    assert failed.status_code == 503

    retry = post_chat(client, "s-retry", "What is the capital of France?")

    assert retry.status_code == 200
    assert retry.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert retry.json()["metadata"]["key_id"] == "key_1"
    assert provider.call_count == 1
