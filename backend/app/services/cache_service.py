"""LiteLLM built-in response cache configuration.

The cache is owned by LiteLLM (``litellm.cache``), never by a custom
dictionary. Cache hits are detected from LiteLLM's own
``response._hidden_params["cache_hit"]`` flag.
"""

from __future__ import annotations

import logging

import litellm

from app.config import Settings

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cache: litellm.Cache | None = None

    def configure(self) -> None:
        litellm.cache = None
        self._cache = None

        if not self.settings.cache_enabled:
            logger.info("cache_disabled_by_configuration")
            return

        try:
            self._cache = litellm.Cache(
                type="local",
                ttl=self.settings.cache_ttl_seconds,
            )
            litellm.cache = self._cache
            logger.info("cache_configured backend=memory")
        except Exception:
            # A cache misconfiguration must not prevent the API from starting.
            # /health will correctly report cache_enabled=false.
            self._cache = None
            litellm.cache = None
            logger.exception("cache_configuration_failed")

    def warm_cache_hit_path(self) -> None:
        """Import LiteLLM's lazy cache-hit dependencies at startup.

        LiteLLM 1.110 imports its Anthropic/proxy modules on the first cache
        hit. That cold import can take seconds, which would make the first
        cache hit slower than live inference. Warming the path during startup
        keeps every observable cache hit fast.
        """

        if not self.is_enabled:
            return
        try:
            from litellm.llms.anthropic.messages.native import response_cache  # noqa: F401

            logger.info("cache_hit_path_warmed")
        except Exception:
            logger.exception("cache_hit_path_warmup_failed")

    @property
    def is_enabled(self) -> bool:
        return (
            self.settings.cache_enabled
            and self._cache is not None
            and litellm.cache is not None
        )

    def reset(self) -> None:
        litellm.cache = None
        self._cache = None
