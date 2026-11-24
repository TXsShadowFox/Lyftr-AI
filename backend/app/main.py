"""FastAPI application factory and process entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import litellm
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.database import Database
from app.logging_config import configure_logging
from app.routes import chat, health, sessions
from app.services.cache_service import CacheService
from app.services.chat_service import ChatService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        litellm.suppress_debug_info = True

        database = Database(settings.database_url)
        try:
            database.init()
        except Exception:
            # Start in a degraded state so /health can report the failure.
            logger.exception("database_initialization_failed")

        cache_service = CacheService(settings)
        cache_service.configure()
        cache_service.warm_cache_hit_path()
        llm_service = LLMService(settings, cache_service)
        chat_service = ChatService(settings, database, llm_service)

        app.state.settings = settings
        app.state.database = database
        app.state.cache_service = cache_service
        app.state.llm_service = llm_service
        app.state.chat_service = chat_service

        logger.info(
            "startup_complete environment=%s keys_configured=%d cache_enabled=%s "
            "failure_simulation=%s",
            settings.environment,
            settings.key_count,
            cache_service.is_enabled,
            settings.enable_failure_simulation,
        )

        try:
            yield
        finally:
            cache_service.reset()
            database.dispose()
            logger.info("shutdown_complete")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Reliable AI. Every Response. A conversational API with automatic "
            "provider-key failover, LiteLLM response caching and SQLite memory."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"^https://.*\.vercel\.app$" if "*" not in settings.cors_origins else None,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        max_age=600,
    )

    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(sessions.router)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "tagline": "Reliable AI. Every Response.",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
