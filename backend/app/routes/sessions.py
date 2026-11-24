"""Session history endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas import SessionMessagesResponse

router = APIRouter(tags=["sessions"])


@router.get(
    "/sessions/{session_id}/messages",
    response_model=SessionMessagesResponse,
    response_model_exclude_none=True,
    summary="Read a session's conversation history",
)
def get_session_messages(session_id: str, request: Request) -> SessionMessagesResponse:
    chat_service = request.app.state.chat_service
    response = chat_service.get_messages(session_id)
    if response is None:
        raise HTTPException(status_code=404, detail="session not found")
    return response
