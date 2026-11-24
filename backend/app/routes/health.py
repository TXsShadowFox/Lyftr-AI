"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    response_model_exclude_none=True,
    summary="Readiness check",
)
def health(request: Request):
    settings = request.app.state.settings
    database = request.app.state.database
    cache_service = request.app.state.cache_service

    keys_configured = settings.key_count
    cache_enabled = cache_service.is_enabled
    database_ok = database.ping() if database is not None else False

    reasons: list[str] = []
    if not database_ok:
        reasons.append("database unreachable")
    if keys_configured < 2:
        reasons.append("at least two API keys required")
    if not cache_enabled:
        reasons.append("cache disabled")

    if reasons:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "keys_configured": keys_configured,
                "cache_enabled": cache_enabled,
                "detail": "; ".join(reasons),
            },
        )

    return HealthResponse(
        status="ok",
        keys_configured=keys_configured,
        cache_enabled=True,
    )
