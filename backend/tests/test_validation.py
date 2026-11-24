"""POST /chat request validation (HTTP 422)."""

from __future__ import annotations

import pytest

from tests.helpers import db_message_count, post_chat


@pytest.mark.parametrize(
    "payload",
    [
        {"message": "hello"},
        {"session_id": None, "message": "hello"},
        {"session_id": "", "message": "hello"},
        {"session_id": "   ", "message": "hello"},
        {"session_id": "s" * 129, "message": "hello"},
        {"session_id": 123, "message": "hello"},
        {"session_id": "s-1"},
        {"session_id": "s-1", "message": None},
        {"session_id": "s-1", "message": ""},
        {"session_id": "s-1", "message": "   \n\t  "},
        {"session_id": "s-1", "message": "x" * 4001},
        {"session_id": "s-1", "message": 42},
        {"session_id": "s-1", "message": "hello", "system_prompt": "x" * 8001},
        {"session_id": "s-1", "message": "hello", "system_prompt": 99},
    ],
)
def test_invalid_payloads_return_422_without_calling_provider(
    client, provider, settings, payload
):
    response = client.post("/chat", json=payload)

    assert response.status_code == 422
    assert provider.call_count == 0
    assert db_message_count(settings.database_url) == 0


def test_malformed_json_returns_422(client, provider):
    response = client.post(
        "/chat",
        content='{"session_id": "s-1", "message": ',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert provider.call_count == 0
    assert "Traceback" not in response.text


def test_message_length_is_measured_after_trimming(client, provider):
    message = "  " + ("a" * 4000) + "  "

    response = post_chat(client, "s-trim", message)

    assert response.status_code == 200
    assert response.json()["reply"] == "Echo: " + ("a" * 4000)
    assert provider.calls[0]["messages"][-1]["content"] == "a" * 4000


def test_session_id_is_trimmed(client):
    response = post_chat(client, "  s-trimmed  ", "hello")

    assert response.status_code == 200
    assert response.json()["session_id"] == "s-trimmed"


def test_exactly_4000_characters_is_accepted(client):
    response = post_chat(client, "s-4000", "b" * 4000)

    assert response.status_code == 200


def test_unknown_extra_fields_are_ignored(client):
    response = client.post(
        "/chat",
        json={"session_id": "s-extra", "message": "hello", "unexpected": "value"},
    )

    assert response.status_code == 200
