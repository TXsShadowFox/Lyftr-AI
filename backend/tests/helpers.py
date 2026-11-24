"""Small helpers shared by the backend test modules."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi.testclient import TestClient

from app.database import sqlite_path_from_url


def post_chat(
    client: TestClient,
    session_id: str,
    message: str,
    *,
    system_prompt: str | None = None,
    headers: dict[str, str] | None = None,
):
    payload: dict[str, Any] = {"session_id": session_id, "message": message}
    if system_prompt is not None:
        payload["system_prompt"] = system_prompt
    return client.post("/chat", json=payload, headers=headers or {})


def get_messages(client: TestClient, session_id: str):
    return client.get(f"/sessions/{session_id}/messages")


def _connect(database_url: str) -> sqlite3.Connection:
    connection = sqlite3.connect(sqlite_path_from_url(database_url))
    connection.row_factory = sqlite3.Row
    return connection


def db_rows(database_url: str) -> list[sqlite3.Row]:
    with _connect(database_url) as connection:
        return connection.execute(
            "SELECT id, session_id, role, content, metadata, created_at "
            "FROM messages ORDER BY id ASC"
        ).fetchall()


def db_message_count(database_url: str) -> int:
    with _connect(database_url) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0])


def db_session_row(database_url: str, session_id: str) -> sqlite3.Row | None:
    with _connect(database_url) as connection:
        return connection.execute(
            "SELECT id, system_prompt, created_at, updated_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
