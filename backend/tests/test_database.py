"""SQLite schema, ordering and persistence."""

from __future__ import annotations

import sqlite3

import pytest

from app.database import Database, sqlite_path_from_url


def test_required_messages_schema_is_created(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'schema.db'}")
    database.init()

    with sqlite3.connect(sqlite_path_from_url(database.database_url)) as connection:
        columns = connection.execute("PRAGMA table_info(messages)").fetchall()

    by_name = {column[1]: column for column in columns}
    assert set(by_name) == {
        "id",
        "session_id",
        "role",
        "content",
        "metadata",
        "created_at",
    }
    assert by_name["id"][5] == 1  # primary key
    assert by_name["session_id"][3] == 1  # NOT NULL
    assert by_name["role"][3] == 1
    assert by_name["content"][3] == 1
    assert by_name["created_at"][3] == 1
    database.dispose()


def test_role_check_constraint(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'roles.db'}")
    database.init()

    with database.connection() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO messages (session_id, role, content, created_at) "
                "VALUES ('s', 'system', 'nope', '2026-01-01T00:00:00+00:00')"
            )
    database.dispose()


def test_exchange_is_stored_and_returned_in_order(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'order.db'}")
    database.init()

    database.save_exchange(
        session_id="s-order",
        system_prompt="prompt",
        user_content="first",
        assistant_content="answer one",
        assistant_metadata='{"resolution_source":"LIVE_INFERENCE"}',
        user_created_at="2026-01-01T00:00:00+00:00",
        assistant_created_at="2026-01-01T00:00:01+00:00",
    )
    database.save_exchange(
        session_id="s-order",
        system_prompt="prompt",
        user_content="second",
        assistant_content="answer two",
        assistant_metadata='{"resolution_source":"LLM_CACHE"}',
        user_created_at="2026-01-01T00:00:02+00:00",
        assistant_created_at="2026-01-01T00:00:03+00:00",
    )

    session_row, messages = database.get_conversation("s-order")

    assert session_row is not None
    assert session_row.system_prompt == "prompt"
    assert [message.content for message in messages] == [
        "first",
        "answer one",
        "second",
        "answer two",
    ]
    assert [message.role for message in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    database.dispose()


def test_data_survives_new_database_instance(tmp_path):
    url = f"sqlite:///{tmp_path / 'persist.db'}"
    first = Database(url)
    first.init()
    first.save_exchange(
        session_id="s-persist",
        system_prompt=None,
        user_content="hello",
        assistant_content="hi",
        assistant_metadata="{}",
        user_created_at="2026-01-01T00:00:00+00:00",
        assistant_created_at="2026-01-01T00:00:01+00:00",
    )
    first.dispose()

    second = Database(url)
    second.init()
    session_row, messages = second.get_conversation("s-persist")

    assert session_row is not None
    assert [message.content for message in messages] == ["hello", "hi"]
    second.dispose()
