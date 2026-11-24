"""Chat endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from app.schemas import ChatRequest, ChatResponse
from app.services.failover_service import AllProvidersUnavailableError

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send one user message and receive the assistant reply",
)
def chat(
    payload: ChatRequest,
    request: Request,
    x_simulate_failure: str | None = Header(
        default=None,
        alias="X-Simulate-Failure",
        description="Testing-only key failure simulation, e.g. key_1=429",
    ),
) -> ChatResponse:
    chat_service = request.app.state.chat_service
    try:
        return chat_service.chat(payload, x_simulate_failure)
    except AllProvidersUnavailableError:
        # Deliberately generic: no provider stack traces, URLs or secrets.
        raise HTTPException(status_code=503, detail="all providers unavailable")
