"""LiteLLM built-in cache behavior and cache identity."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import post_chat


def test_first_request_is_a_cache_miss(client, provider):
    response = post_chat(client, "s-cache-1", "What is the capital of France?")

    metadata = response.json()["metadata"]
    assert metadata["resolution_source"] == "LIVE_INFERENCE"
    assert metadata["key_id"] == "key_1"
    assert metadata["fallback_attempts"] == 0
    assert provider.call_count == 1


def test_identical_first_message_in_new_session_hits_cache(client, provider):
    first = post_chat(client, "s-cache-a", "What is the capital of France?")
    second = post_chat(client, "s-cache-b", "What is the capital of France?")

    assert first.status_code == second.status_code == 200
    first_body = first.json()
    second_body = second.json()

    assert second_body["reply"] == first_body["reply"]
    metadata = second_body["metadata"]
    assert metadata["resolution_source"] == "LLM_CACHE"
    assert metadata["key_id"] is None
    assert metadata["fallback_attempts"] == 0
    # LiteLLM restores the token usage captured for the cached response.
    assert metadata["input_tokens"] == first_body["metadata"]["input_tokens"]
    assert metadata["output_tokens"] == first_body["metadata"]["output_tokens"]
    # The second request never reached the provider.
    assert provider.call_count == 1


def test_different_message_does_not_reuse_cached_response(client, provider):
    first = post_chat(client, "s-cache-diff-a", "What is the capital of France?")
    second = post_chat(client, "s-cache-diff-b", "Tell me about tokens")

    assert second.json()["reply"] != first.json()["reply"]
    assert second.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert provider.call_count == 2


def test_cache_identity_includes_full_history(client, provider):
    # Build a two-turn conversation that is cached under its full history.
    post_chat(client, "s-history-a", "alpha")
    post_chat(client, "s-history-a", "beta")
    assert provider.call_count == 2

    # A different first turn changes the history for the same second message.
    post_chat(client, "s-history-b", "gamma")
    different_history = post_chat(client, "s-history-b", "beta")
    assert different_history.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert provider.call_count == 4

    # Replaying the exact same conversation is served entirely from cache.
    replay_one = post_chat(client, "s-history-c", "alpha")
    replay_two = post_chat(client, "s-history-c", "beta")
    assert replay_one.json()["metadata"]["resolution_source"] == "LLM_CACHE"
    assert replay_two.json()["metadata"]["resolution_source"] == "LLM_CACHE"
    assert replay_two.json()["reply"] == "Echo: beta"
    assert provider.call_count == 4


def test_changed_system_prompt_changes_cache_identity(client, provider):
    plain = post_chat(client, "s-prompt-a", "What is the capital of France?")
    terse = post_chat(
        client,
        "s-prompt-b",
        "What is the capital of France?",
        system_prompt="You are terse.",
    )
    same_terse = post_chat(
        client,
        "s-prompt-c",
        "What is the capital of France?",
        system_prompt="You are terse.",
    )
    verbose = post_chat(
        client,
        "s-prompt-d",
        "What is the capital of France?",
        system_prompt="You are verbose.",
    )

    assert plain.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert terse.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert same_terse.json()["metadata"]["resolution_source"] == "LLM_CACHE"
    assert verbose.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert provider.call_count == 3


def test_cache_hit_is_faster_than_live_inference(client, provider):
    provider.delay_seconds = 0.2

    live = post_chat(client, "s-speed-a", "What is the capital of France?")
    cached = post_chat(client, "s-speed-b", "What is the capital of France?")

    live_latency = live.json()["metadata"]["latency_ms"]
    cached_latency = cached.json()["metadata"]["latency_ms"]
    assert live_latency >= 150
    assert cached_latency < live_latency
    assert provider.call_count == 1


def test_cache_can_be_disabled(make_settings, provider):
    settings = make_settings(cache_enabled=False)
    with TestClient(create_app(settings)) as client:
        first = post_chat(client, "s-nocache-a", "What is the capital of France?")
        second = post_chat(client, "s-nocache-b", "What is the capital of France?")

    assert first.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert second.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert provider.call_count == 2
