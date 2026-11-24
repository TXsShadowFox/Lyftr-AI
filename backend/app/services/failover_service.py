"""Failure simulation parsing and provider error classification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

SIMULATABLE_STATUSES = frozenset({429, 500, 502, 503})
_KEY_ID_PATTERN = re.compile(r"^key_[1-9][0-9]*$")


class AllProvidersUnavailableError(RuntimeError):
    """Raised when every configured key has been exhausted."""


class EmptyProviderResponseError(RuntimeError):
    """Raised when a provider returns a successful but unusable response."""


@dataclass(frozen=True)
class ProviderFailure:
    status_code: int | None
    error_type: str


def parse_failure_header(raw_header: str | None) -> dict[str, int]:
    """Parse ``X-Simulate-Failure`` into ``{key_id|"*": status}``.

    Malformed entries are ignored rather than failing the request. Only the
    statuses explicitly supported by the assignment are accepted.
    """

    if not raw_header:
        return {}

    parsed: dict[str, int] = {}
    for entry in raw_header.split(","):
        target, separator, status_text = entry.partition("=")
        if not separator:
            continue
        target = target.strip()
        if target != "*" and not _KEY_ID_PATTERN.match(target):
            continue
        try:
            status = int(status_text.strip())
        except ValueError:
            continue
        if status in SIMULATABLE_STATUSES:
            parsed[target] = status
    return parsed


def simulated_status_for(key_id: str, simulation: dict[str, int]) -> int | None:
    """Specific key rules take precedence over the wildcard rule."""

    if key_id in simulation:
        return simulation[key_id]
    return simulation.get("*")


def provider_failure(exc: BaseException) -> ProviderFailure:
    """Extract a status code without retaining exception text (which may
    contain request details or credentials)."""

    status: int | None = None
    for attribute in ("status_code", "code"):
        value = getattr(exc, attribute, None)
        if isinstance(value, int):
            status = value
            break
        if isinstance(value, str) and value.isdigit():
            status = int(value)
            break

    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)

    return ProviderFailure(
        status_code=status if isinstance(status, int) else None,
        error_type=type(exc).__name__,
    )


def is_retryable_failure(exc: BaseException) -> bool:
    """A key failure should move the request to the next key.

    We retry every provider-side failure. This covers 429/quota, 5xx,
    auth/revoked keys, timeouts and transport errors. The pool is bounded, so
    a permanently failing provider still terminates with 503.
    """

    return not isinstance(exc, (KeyboardInterrupt, SystemExit, MemoryError))


def describe_error(exc: BaseException) -> str:
    failure = provider_failure(exc)
    if failure.status_code is not None:
        return f"{failure.error_type}({failure.status_code})"
    return failure.error_type


def safe_exception_detail(exc: BaseException) -> dict[str, Any]:
    """Structured, secret-free data for logs/tests."""

    failure = provider_failure(exc)
    return {
        "error_type": failure.error_type,
        "status_code": failure.status_code,
    }
