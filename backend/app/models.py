"""Typed row objects for the SQLite data layer."""

from __future__ import annotations

from dataclasses import dataclass
from sqlite3 import Row


@dataclass(frozen=True)
class SessionRow:
    id: str
    system_prompt: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: Row) -> "SessionRow":
        return cls(
            id=row["id"],
            system_prompt=row["system_prompt"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass(frozen=True)
class MessageRow:
    id: int
    session_id: str
    role: str
    content: str
    metadata_json: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: Row) -> "MessageRow":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            metadata_json=row["metadata"],
            created_at=row["created_at"],
        )
