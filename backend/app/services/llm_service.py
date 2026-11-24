"""LiteLLM gateway with real per-key failover.

Each attempt passes a different ``api_key`` to ``litellm.completion``. The
metadata is derived from what actually happened: the key that produced the
successful response, the number of keys that failed first, and LiteLLM's own
cache-hit flag.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import litellm

from app.config import Settings
from app.services.cache_service import CacheService
from app.services.failover_service import (
    AllProvidersUnavailableError,
    EmptyProviderResponseError,
    describe_error,
    is_retryable_failure,
    parse_failure_header,
    simulated_status_for,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ApiKey:
    id: str
    value: str


@dataclass(frozen=True)
class LLMResult:
    reply: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    key_id: str | None
    fallback_attempts: int
    resolution_source: str


CompletionFn = Callable[..., Any]


class LLMService:
    def __init__(
        self,
        settings: Settings,
        cache_service: CacheService,
        completion_fn: CompletionFn | None = None,
    ) -> None:
        self.settings = settings
        self.cache_service = cache_service
        self._completion: CompletionFn = completion_fn or litellm.completion
        self.keys: tuple[ApiKey, ...] = tuple(
            ApiKey(id=f"key_{index}", value=value)
            for index, value in enumerate(settings.api_keys, start=1)
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        simulate_failure_header: str | None = None,
    ) -> LLMResult:
        started = time.perf_counter()
        simulation = (
            parse_failure_header(simulate_failure_header)
            if self.settings.enable_failure_simulation
            else {}
        )
        # A simulated failure must never be served from an existing cache entry,
        # and must never write a cache entry of its own.
        cache_controls = {"no-cache": True, "no-store": True} if simulation else None

        failed_attempts = 0
        last_error: BaseException | None = None

        if not self.keys:
            logger.error("llm_pool_empty")
            raise AllProvidersUnavailableError("no keys configured")

        for key in self.keys:
            simulated_status = simulated_status_for(key.id, simulation)
            if simulated_status is not None:
                failed_attempts += 1
                logger.info(
                    "llm_key_simulated_failure key_id=%s status=%s attempt=%d",
                    key.id,
                    simulated_status,
                    failed_attempts,
                )
                continue

            kwargs: dict[str, Any] = {
                "model": self.settings.llm_model,
                "messages": messages,
                "api_key": key.value,
                "temperature": self.settings.llm_temperature,
                "timeout": self.settings.llm_request_timeout,
                "num_retries": self.settings.llm_num_retries,
                # Prevent the OpenAI SDK from retrying the same failed key
                # behind our back; failover is owned by this service.
                "max_retries": 0,
            }
            if self.settings.llm_api_base:
                kwargs["api_base"] = self.settings.llm_api_base
            else:
                # When using real providers without an override api_base, route keys
                # from different providers (e.g. Gemini direct and OpenRouter gateway) correctly.
                if key.value.startswith("sk-or-"):
                    if kwargs["model"].startswith("gemini/"):
                        raw_model = kwargs["model"].removeprefix("gemini/")
                        if raw_model in ("gemini-2.0-flash", "gemini-2.0-flash-001"):
                            kwargs["model"] = "openrouter/google/gemini-2.0-flash-001"
                        else:
                            kwargs["model"] = f"openrouter/google/{raw_model}"
                    elif not kwargs["model"].startswith("openrouter/"):
                        kwargs["model"] = f"openrouter/{kwargs['model']}"
                elif kwargs["model"].startswith("openrouter/google/"):
                    kwargs["model"] = "gemini/" + kwargs["model"].removeprefix("openrouter/google/")

            if self.settings.llm_max_tokens is not None:
                kwargs["max_tokens"] = self.settings.llm_max_tokens
            if cache_controls is not None:
                kwargs["cache"] = cache_controls

            try:
                response = self._completion(**kwargs)
                reply = _extract_reply(response)
                if not reply.strip():
                    raise EmptyProviderResponseError("provider returned an empty reply")

                hidden = getattr(response, "_hidden_params", None) or {}
                cache_hit = hidden.get("cache_hit") is True
                input_tokens, output_tokens = _extract_usage(response)
                latency_ms = max(0, int(round((time.perf_counter() - started) * 1000)))

                if cache_hit:
                    logger.info(
                        "llm_cache_hit model=%s latency_ms=%d",
                        self.settings.llm_model,
                        latency_ms,
                    )
                    return LLMResult(
                        reply=reply,
                        model=self.settings.llm_model,
                        latency_ms=latency_ms,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        key_id=None,
                        fallback_attempts=0,
                        resolution_source="LLM_CACHE",
                    )

                logger.info(
                    "llm_live_success key_id=%s fallback_attempts=%d latency_ms=%d",
                    key.id,
                    failed_attempts,
                    latency_ms,
                )
                return LLMResult(
                    reply=reply,
                    model=self.settings.llm_model,
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    key_id=key.id,
                    fallback_attempts=failed_attempts,
                    resolution_source="LIVE_INFERENCE",
                )
            except Exception as exc:  # provider failures must become failover
                if not is_retryable_failure(exc):
                    raise
                last_error = exc
                failed_attempts += 1
                logger.warning(
                    "llm_key_failed key_id=%s error=%s attempt=%d",
                    key.id,
                    describe_error(exc),
                    failed_attempts,
                )
                continue

        logger.error(
            "llm_pool_exhausted attempts=%d last_error=%s",
            failed_attempts,
            describe_error(last_error) if last_error else "simulated",
        )
        raise AllProvidersUnavailableError("all providers unavailable")


def _extract_reply(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if not choices:
        raise EmptyProviderResponseError("provider returned no choices")

    message = getattr(choices[0], "message", None)
    if message is None and isinstance(choices[0], dict):
        message = choices[0].get("message")

    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")

    if isinstance(content, str):
        return content

    # Some providers return a list of content parts.
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
            else:
                text = getattr(part, "text", None)
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)

    raise EmptyProviderResponseError("provider returned no text content")


def _extract_usage(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0

    def read(*names: str) -> int:
        for name in names:
            value = getattr(usage, name, None)
            if value is None and isinstance(usage, dict):
                value = usage.get(name)
            if value is not None:
                try:
                    return max(0, int(value))
                except (TypeError, ValueError):
                    continue
        return 0

    return read("prompt_tokens", "input_tokens"), read(
        "completion_tokens", "output_tokens"
    )
