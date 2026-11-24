"""Chat, multi-turn memory, session isolation and persistence."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import db_session_row, get_messages, post_chat


def test_valid_chat_request_returns_contract(client, provider):
    response = post_chat(client, "s-valid", "What is the capital of France?")

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "s-valid"
    assert body["reply"] == "The capital of France is Paris."

    metadata = body["metadata"]
    assert metadata["resolution_source"] == "LIVE_INFERENCE"
    assert metadata["model"] == "openai/lyftr-mock"
    assert metadata["key_id"] == "key_1"
    assert metadata["fallback_attempts"] == 0
    assert isinstance(metadata["latency_ms"], int)
    assert metadata["latency_ms"] >= 0
    assert metadata["input_tokens"] > 0
    assert metadata["output_tokens"] > 0
    assert provider.call_count == 1


def test_multi_turn_memory_sends_full_history_and_returns_it(client, provider):
    first = post_chat(client, "s-memory", "hello")
    assert first.status_code == 200

    second = post_chat(client, "s-memory", "remember the earlier turn")
    assert second.status_code == 200
    assert second.json()["reply"] == "I remember the earlier turn."

    # The provider received the full history in order, and only the new
    # message was appended for the second request.
    assert provider.calls[1]["messages"] == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "Echo: hello"},
        {"role": "user", "content": "remember the earlier turn"},
    ]

    history = get_messages(client, "s-memory")
    assert history.status_code == 200
    body = history.json()
    assert body["session_id"] == "s-memory"
    assert [m["role"] for m in body["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert body["messages"][0] == {"role": "user", "content": "hello"}
    assert body["messages"][1]["content"] == "Echo: hello"
    assert body["messages"][2] == {
        "role": "user",
        "content": "remember the earlier turn",
    }
    assert body["messages"][3]["metadata"] == second.json()["metadata"]


def test_sessions_are_isolated(client, provider):
    post_chat(client, "s-a", "alpha")
    post_chat(client, "s-b", "beta")

    history_a = get_messages(client, "s-a").json()
    history_b = get_messages(client, "s-b").json()

    assert [m["content"] for m in history_a["messages"]] == ["alpha", "Echo: alpha"]
    assert [m["content"] for m in history_b["messages"]] == ["beta", "Echo: beta"]
    assert provider.calls[1]["messages"] == [{"role": "user", "content": "beta"}]


def test_unknown_session_returns_exact_404(client):
    response = get_messages(client, "s-does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "session not found"}


def test_system_prompt_is_used_stored_and_never_exposed_as_message(client, provider, settings):
    response = post_chat(
        client,
        "s-prompt",
        "hello",
        system_prompt="You are terse.",
    )
    assert response.status_code == 200
    assert provider.calls[0]["messages"][0] == {
        "role": "system",
        "content": "You are terse.",
    }

    # Omitting the field reuses the session prompt.
    post_chat(client, "s-prompt", "again")
    assert provider.calls[1]["messages"][0] == {
        "role": "system",
        "content": "You are terse.",
    }

    history = get_messages(client, "s-prompt").json()
    assert all(m["role"] != "system" for m in history["messages"])
    assert "You are terse." not in [m["content"] for m in history["messages"]]

    stored = db_session_row(settings.database_url, "s-prompt")
    assert stored is not None
    assert stored["system_prompt"] == "You are terse."


def test_empty_system_prompt_clears_stored_prompt(client, provider, settings):
    post_chat(client, "s-clear", "hello", system_prompt="Be concise.")
    post_chat(client, "s-clear", "second", system_prompt="")

    assert all(m["role"] != "system" for m in provider.calls[1]["messages"])
    stored = db_session_row(settings.database_url, "s-clear")
    assert stored is not None
    assert stored["system_prompt"] is None


def test_history_survives_application_restart(settings, provider):
    with TestClient(create_app(settings)) as first:
        assert post_chat(first, "s-persist", "hello").status_code == 200

    with TestClient(create_app(settings)) as second:
        response = get_messages(second, "s-persist")

    assert response.status_code == 200
    body = response.json()
    assert [m["content"] for m in body["messages"]] == ["hello", "Echo: hello"]
    assert body["messages"][1]["metadata"]["resolution_source"] == "LIVE_INFERENCE"


def test_failed_session_is_not_visible(client, provider):
    response = post_chat(
        client,
        "s-never",
        "hello",
        headers={"X-Simulate-Failure": "*=503"},
    )

    assert response.status_code == 503
    assert get_messages(client, "s-never").status_code == 404
