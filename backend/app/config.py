"""Application configuration.

All secrets are read from the environment. Nothing in this module is ever
serialized or logged: the parsed key list is exposed only through the
``api_keys`` property, which callers must treat as secret material.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "LYFTR AI"
    app_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    # --- Persistence -----------------------------------------------------
    # The deployed value is sqlite:////data/app.db (four slashes = absolute).
    database_url: str = "sqlite:///./data/app.db"

    # --- LLM gateway -----------------------------------------------------
    llm_api_keys: str = ""
    llm_model: str = "gemini/gemini-3.5-flash-lite"
    llm_api_base: str | None = None
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_max_tokens: int | None = Field(default=None, ge=1)
    llm_request_timeout: float = Field(default=60.0, gt=0.0, le=300.0)
    llm_num_retries: int = Field(default=0, ge=0, le=5)

    # --- LiteLLM response cache -----------------------------------------
    # LiteLLM's built-in in-memory cache is used. No external cache services.
    cache_enabled: bool = True
    cache_ttl_seconds: int | None = Field(default=None, ge=1)

    # --- HTTP ------------------------------------------------------------
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    enable_failure_simulation: bool = False

    @field_validator("database_url")
    @classmethod
    def _require_sqlite(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith(("sqlite:///", "sqlite+pysqlite:///")):
            raise ValueError("DATABASE_URL must be a SQLite URL")
        return normalized

    @field_validator("llm_api_base", mode="before")
    @classmethod
    def _empty_api_base_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def api_keys(self) -> list[str]:
        """Return configured keys in stable order, preserving duplicates.

        Values are never logged. A key is considered configured only when it
        has non-whitespace content.
        """

        return [part.strip() for part in self.llm_api_keys.split(",") if part.strip()]

    @property
    def key_count(self) -> int:
        return len(self.api_keys)

    @property
    def cors_origins(self) -> list[str]:
        origins = [part.strip() for part in self.allowed_origins.split(",") if part.strip()]
        if "*" in origins:
            return ["*"]
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
