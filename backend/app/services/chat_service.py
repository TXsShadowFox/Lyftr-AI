"""Conversation orchestration: history, prompt, LLM call and persistence."""

from __future__ import annotations

import json
import logging

from app.config import Settings
from app.database import Database
from app.models import MessageRow
from app.schemas import ChatMetadata, ChatRequest, ChatResponse, SessionMessagesResponse, StoredMessage
from app.services.llm_service import LLMService
from app.utils import utc_now_iso

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, settings: Settings, database: Database, llm_service: LLMService) -> None:
        self.settings = settings
        self.database = database
        self.llm_service = llm_service

    def chat(self, request: ChatRequest, simulate_failure_header: str | None) -> ChatResponse:
        request_started_at = utc_now_iso()

        session_row, history_rows = self.database.get_conversation(request.session_id)
        stored_prompt = session_row.system_prompt if session_row else None

        # An explicitly supplied prompt (including an empty string, which clears
        # it) wins. Omitting the field reuses the session's stored prompt.
        if request.system_prompt is not None:
            effective_prompt = request.system_prompt or None
        else:
            effective_prompt = stored_prompt

        llm_messages = _build_llm_messages(
            system_prompt=effective_prompt,
            history=history_rows,
            current_message=request.message,
        )

        result = self.llm_service.complete(llm_messages, simulate_failure_header)
        completed_at = utc_now_iso()

        metadata = ChatMetadata(
            resolution_source=result.resolution_source,  # type: ignore[arg-type]
            model=result.model,
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            key_id=result.key_id,
            fallback_attempts=result.fallback_attempts,
        )

        # Only a successful exchange reaches this point. The session upsert,
        # user message and assistant message are one SQLite transaction.
        self.database.save_exchange(
            session_id=request.session_id,
            system_prompt=effective_prompt,
            user_content=request.message,
            assistant_content=result.reply,
            assistant_metadata=metadata.model_dump_json(),
            user_created_at=request_started_at,
            assistant_created_at=completed_at,
        )

        return ChatResponse(
            session_id=request.session_id,
            reply=result.reply,
            metadata=metadata,
        )

    def get_messages(self, session_id: str) -> SessionMessagesResponse | None:
        session_row, message_rows = self.database.get_conversation(session_id)
        if session_row is None:
            return None

        messages: list[StoredMessage] = []
        for row in message_rows:
            messages.append(
                StoredMessage(
                    role=row.role,  # type: ignore[arg-type]
                    content=row.content,
                    metadata=_parse_metadata(row.metadata_json),
                )
            )

        return SessionMessagesResponse(session_id=session_id, messages=messages)


def _build_llm_messages(
    system_prompt: str | None,
    history: list[MessageRow],
    current_message: str,
) -> list[dict[str, str]]:
    """The cache identity is the full LiteLLM message list.

    No session ID, request ID or metadata is included, so identical
    conversations share a cache entry across sessions while any change to the
    system prompt, history or current message produces a different key.
    """

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend({"role": row.role, "content": row.content} for row in history)
    messages.append({"role": "user", "content": current_message})
    return messages


def _parse_metadata(raw: str | None) -> ChatMetadata | None:
    if not raw:
        return None
    try:
        payload = json.loads(raw)
        return ChatMetadata.model_validate(payload)
    except Exception:
        logger.warning("stored_message_metadata_invalid")
        return None
