"""Local OpenAI-compatible mock provider (development only).

This is NOT part of the production backend and is never used by the deployed
app. It exists so the UI, LiteLLM integration, caching and failover can be
exercised end-to-end without real provider credentials.

Run:
    python scripts/mock_llm.py

Then point the backend at it:
    LLM_MODEL=openai/lyftr-mock
    LLM_API_BASE=http://127.0.0.1:9999/v1
    LLM_API_KEYS=demo-key-1,demo-key-2
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="LYFTR AI local mock provider", docs_url=None, redoc_url=None)

DELAY_MS = int(os.getenv("MOCK_DELAY_MS", "0"))
FAIL_KEY = os.getenv("MOCK_FAIL_KEY", "").strip()
FAIL_STATUS = int(os.getenv("MOCK_FAIL_STATUS", "500"))


def _reply_for(messages: list[dict[str, Any]]) -> str:
    last_user = next(
        (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
        "",
    )
    normalized = last_user.lower()

    if "capital of france" in normalized:
        return "The capital of France is Paris."
    if "who are you" in normalized or "what are you" in normalized:
        return (
            "I am LYFTR AI, a reliability-focused assistant. This reply comes from "
            "the local mock provider used for development verification; the "
            "production path uses LiteLLM with real provider credentials."
        )
    if "failover" in normalized:
        return (
            "LYFTR AI routes each request through an ordered pool of provider keys. "
            "If a key returns 429, quota exhaustion or a 5xx response, the next key "
            "is tried automatically. The response metadata reports the successful "
            "key and how many keys failed first."
        )
    if "cache" in normalized:
        return (
            "Repeated conversations are served by LiteLLM's built-in response cache. "
            "A cache hit is labelled LLM_CACHE and reuses the original token usage, "
            "without calling the provider again."
        )
    if "history" in normalized or "remember" in normalized:
        return (
            "Conversation history is stored in SQLite and keyed by session ID. "
            "Each new message is sent alone; the backend reconstructs the full "
            "conversation before calling the model."
        )

    return (
        "This is a deterministic reply from the local mock provider. "
        f"You said: \"{last_user[:240]}\". "
        "Start the backend with real provider keys to receive live model output."
    )


def _token_count(text: str) -> int:
    return max(1, len(text.split()))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "provider": "local-mock"}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    if DELAY_MS > 0:
        await asyncio.sleep(DELAY_MS / 1000)

    auth = request.headers.get("authorization", "")
    key_id = auth.replace("Bearer ", "").strip()

    if FAIL_KEY and key_id == FAIL_KEY:
        return JSONResponse(
            status_code=FAIL_STATUS,
            content={
                "error": {
                    "message": "simulated provider failure",
                    "type": "mock_provider_error",
                    "code": str(FAIL_STATUS),
                }
            },
        )

    body = await request.json()
    messages = body.get("messages", [])
    reply = _reply_for(messages)
    prompt_tokens = sum(_token_count(str(m.get("content", ""))) for m in messages)
    completion_tokens = _token_count(reply)

    return {
        "id": f"chatcmpl-mock-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model", "lyftr-mock"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("MOCK_HOST", "127.0.0.1"),
        port=int(os.getenv("MOCK_PORT", "9999")),
        log_level="warning",
    )
