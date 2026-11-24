"""Per-request token accounting, metadata and SQLite record shape."""

from __future__ import annotations

import json
from datetime import datetime

from tests.helpers import db_rows, get_messages, post_chat

METADATA_KEYS = {
    "resolution_source",
    "model",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "key_id",
    "fallback_attempts",
}


def test_metadata_has_exact_shape_and_types(client):
    metadata = post_chat(client, "s-meta", "hello").json()["metadata"]

    assert set(metadata) == METADATA_KEYS
    assert metadata["resolution_source"] in {"LIVE_INFERENCE", "LLM_CACHE"}
    assert isinstance(metadata["model"], str) and metadata["model"]
    assert type(metadata["latency_ms"]) is int
    assert type(metadata["input_tokens"]) is int
    assert type(metadata["output_tokens"]) is int
    assert metadata["key_id"] in {"key_1", "key_2", None}
    assert type(metadata["fallback_attempts"]) is int


def test_token_usage_is_per_request_not_accumulated(client, provider):
    first = post_chat(client, "s-tokens", "hello").json()
    second = post_chat(client, "s-tokens", "tell me about token usage").json()

    first_usage = provider.calls[0]["usage"]
    second_usage = provider.calls[1]["usage"]

    assert first["metadata"]["input_tokens"] == first_usage["prompt_tokens"]
    assert first["metadata"]["output_tokens"] == first_usage["completion_tokens"]
    assert second["metadata"]["input_tokens"] == second_usage["prompt_tokens"]
    assert second["metadata"]["output_tokens"] == second_usage["completion_tokens"]

    # The second prompt contains the first exchange, so it is larger, but the
    # reported numbers are that request's usage, not a running total.
    assert second_usage["prompt_tokens"] > first_usage["prompt_tokens"]
    assert second["metadata"]["input_tokens"] < (
        first["metadata"]["input_tokens"] + second_usage["prompt_tokens"]
    )


def test_history_returns_assistant_metadata_and_no_user_metadata(client):
    response = post_chat(client, "s-history-meta", "hello").json()

    messages = get_messages(client, "s-history-meta").json()["messages"]

    assert messages[0] == {"role": "user", "content": "hello"}
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == response["reply"]
    assert messages[1]["metadata"] == response["metadata"]


def test_sqlite_rows_store_metadata_json_and_iso_timestamps(client, settings):
    response = post_chat(client, "s-rows", "hello").json()
    rows = db_rows(settings.database_url)

    assert [row["role"] for row in rows] == ["user", "assistant"]
    assert [row["session_id"] for row in rows] == ["s-rows", "s-rows"]

    user_row, assistant_row = rows
    assert user_row["metadata"] is None
    stored_metadata = json.loads(assistant_row["metadata"])
    assert stored_metadata == response["metadata"]

    for row in rows:
        # Python 3.11+ parses the trailing "Z" emitted by the app.
        parsed = datetime.fromisoformat(row["created_at"])
        assert parsed.tzinfo is not None
        assert row["created_at"].endswith(("Z", "+00:00"))

    assert user_row["created_at"] <= assistant_row["created_at"]


def test_metadata_is_not_shared_between_messages(client):
    first = post_chat(client, "s-shared-meta", "hello").json()["metadata"]
    second = post_chat(client, "s-shared-meta", "tell me about tokens").json()["metadata"]

    messages = get_messages(client, "s-shared-meta").json()["messages"]
    assert messages[1]["metadata"] == first
    assert messages[3]["metadata"] == second
    assert messages[1]["metadata"] != messages[3]["metadata"]


def test_model_name_is_the_configured_litellm_model(client, settings):
    metadata = post_chat(client, "s-model", "hello").json()["metadata"]

    assert metadata["model"] == settings.llm_model
