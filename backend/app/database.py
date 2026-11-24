"""SQLite persistence layer.

The assignment requires SQLite and permits SQLAlchemy "or a clean equivalent
database layer". This module is a deliberately small stdlib ``sqlite3``
repository: schema creation, health checks, conversation reads and atomic
exchange writes. It uses WAL mode, a busy timeout and one short-lived
connection per operation so FastAPI's threadpool is safe.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.models import MessageRow, SessionRow

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    system_prompt TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_messages_session_id_id
    ON messages (session_id, id);
"""


def sqlite_path_from_url(database_url: str) -> str:
    """Translate ``sqlite:///...`` into a filesystem path.

    ``sqlite:///./data/app.db`` -> ``./data/app.db``
    ``sqlite:////data/app.db``  -> ``/data/app.db``
    """

    if database_url.startswith("sqlite+pysqlite:///"):
        remainder = database_url[len("sqlite+pysqlite:///") :]
    elif database_url.startswith("sqlite:///"):
        remainder = database_url[len("sqlite:///") :]
    else:
        raise ValueError("Only SQLite database URLs are supported")

    if not remainder:
        raise ValueError("SQLite database path is empty")
    return remainder


class Database:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.path = sqlite_path_from_url(database_url)
        self._is_memory = self.path == ":memory:"
        self._uri = False
        self._target = self.path
        self._anchor: sqlite3.Connection | None = None

        if self._is_memory:
            # Shared-cache memory DB so every short-lived connection sees the
            # same schema. An anchor connection keeps it alive.
            self._target = "file:lyftr_memory?mode=memory&cache=shared"
            self._uri = True
            self._anchor = self._connect()
        else:
            parent = Path(self.path).expanduser().resolve().parent
            parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._target,
            timeout=5.0,
            check_same_thread=False,
            uri=self._uri,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def init(self) -> None:
        with self.connection() as connection:
            connection.executescript(SCHEMA)

    def ping(self) -> bool:
        try:
            with self.connection() as connection:
                connection.execute("SELECT 1").fetchone()
            return True
        except Exception:
            logger.exception("database_health_check_failed")
            return False

    def get_conversation(
        self, session_id: str
    ) -> tuple[SessionRow | None, list[MessageRow]]:
        with self.connection() as connection:
            session_row = connection.execute(
                "SELECT id, system_prompt, created_at, updated_at "
                "FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            message_rows = connection.execute(
                "SELECT id, session_id, role, content, metadata, created_at "
                "FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        return (
            SessionRow.from_row(session_row) if session_row else None,
            [MessageRow.from_row(row) for row in message_rows],
        )

    def save_exchange(
        self,
        *,
        session_id: str,
        system_prompt: str | None,
        user_content: str,
        assistant_content: str,
        assistant_metadata: str,
        user_created_at: str,
        assistant_created_at: str,
    ) -> None:
        """Commit the session upsert and both messages atomically."""

        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO sessions (id, system_prompt, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    system_prompt = excluded.system_prompt,
                    updated_at = excluded.updated_at
                """,
                (session_id, system_prompt, user_created_at, assistant_created_at),
            )
            connection.execute(
                """
                INSERT INTO messages (session_id, role, content, metadata, created_at)
                VALUES (?, 'user', ?, NULL, ?)
                """,
                (session_id, user_content, user_created_at),
            )
            connection.execute(
                """
                INSERT INTO messages (session_id, role, content, metadata, created_at)
                VALUES (?, 'assistant', ?, ?, ?)
                """,
                (session_id, assistant_content, assistant_metadata, assistant_created_at),
            )

    def dispose(self) -> None:
        if self._anchor is not None:
            self._anchor.close()
            self._anchor = None
