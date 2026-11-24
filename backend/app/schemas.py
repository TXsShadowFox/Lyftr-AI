"""Pydantic request and response contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ResolutionSource = Literal["LIVE_INFERENCE", "LLM_CACHE"]


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=False)

    session_id: str
    message: str
    system_prompt: str | None = None

    @field_validator("session_id", mode="after")
    @classmethod
    def _validate_session_id(cls, value: str) -> str:
        normalized = value.strip()
        if not 1 <= len(normalized) <= 128:
            raise ValueError("session_id must be between 1 and 128 characters")
        return normalized

    @field_validator("message", mode="after")
    @classmethod
    def _validate_message(cls, value: str) -> str:
        # The assignment specifies 1-4000 characters *after trimming*.
        normalized = value.strip()
        if not 1 <= len(normalized) <= 4000:
            raise ValueError("message must be between 1 and 4000 characters after trimming")
        return normalized

    @field_validator("system_prompt", mode="after")
    @classmethod
    def _normalize_system_prompt(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if len(normalized) > 8000:
            raise ValueError("system_prompt must be at most 8000 characters")
        # Keep "" distinct from None: an explicit empty value clears a stored
        # session prompt, while omitting the field leaves it unchanged.
        return normalized


class ChatMetadata(BaseModel):
    resolution_source: ResolutionSource
    model: str
    latency_ms: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    key_id: str | None = None
    fallback_attempts: int = Field(ge=0)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    metadata: ChatMetadata


class StoredMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    metadata: ChatMetadata | None = None


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: list[StoredMessage]


class HealthResponse(BaseModel):
    status: Literal["ok", "error"]
    keys_configured: int
    cache_enabled: bool
    detail: str | None = None
