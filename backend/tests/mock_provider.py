"""Deterministic OpenAI-compatible provider used by the automated tests.

Tests use the real LiteLLM client, real cache and real failover loop against
this local HTTP server. No provider credentials are required and no network
access leaves the machine.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable


def default_reply(messages: list[dict[str, Any]]) -> str:
    last_user = next(
        (str(message.get("content", "")) for message in reversed(messages) if message.get("role") == "user"),
        "",
    )
    normalized = last_user.lower()
    if "capital of france" in normalized:
        return "The capital of France is Paris."
    if "remember" in normalized:
        return "I remember the earlier turn."
    if "token" in normalized:
        return "Tokens are counted per request, not accumulated."
    return f"Echo: {last_user}"


def word_count(text: str) -> int:
    return max(1, len(text.split()))


class MockProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.failures: dict[str, int] = {}
        self.delay_seconds: float = 0.0
        self.reply_fn: Callable[[list[dict[str, Any]]], str] = default_reply
        self._lock = threading.Lock()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        if self._server is None:
            raise RuntimeError("mock provider is not running")
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}/v1"

    def start(self) -> None:
        provider = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path.rstrip("/") == "/v1/models":
                    self._send_json(
                        200,
                        {
                            "object": "list",
                            "data": [
                                {
                                    "id": "lyftr-mock",
                                    "object": "model",
                                    "created": int(time.time()),
                                    "owned_by": "local-test",
                                }
                            ],
                        },
                    )
                    return
                self._send_json(404, {"error": {"message": "not found"}})

            def do_POST(self) -> None:  # noqa: N802
                if not self.path.endswith("/chat/completions"):
                    self._send_json(404, {"error": {"message": "not found"}})
                    return

                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                try:
                    body = json.loads(raw or b"{}")
                except json.JSONDecodeError:
                    self._send_json(400, {"error": {"message": "invalid json"}})
                    return

                auth = self.headers.get("Authorization", "")
                key = auth.removeprefix("Bearer ").strip()
                messages = body.get("messages", [])

                if provider.delay_seconds > 0:
                    time.sleep(provider.delay_seconds)

                status = provider.failures.get(key)
                with provider._lock:
                    provider.calls.append(
                        {
                            "key": key,
                            "messages": messages,
                            "body": body,
                            "status": status,
                        }
                    )

                if status is not None:
                    self._send_json(
                        status,
                        {
                            "error": {
                                "message": "simulated provider failure",
                                "type": "mock_provider_error",
                                "code": str(status),
                            }
                        },
                    )
                    return

                reply = provider.reply_fn(messages)
                prompt_tokens = sum(word_count(str(m.get("content", ""))) for m in messages)
                completion_tokens = word_count(reply)
                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                }
                with provider._lock:
                    provider.calls[-1]["usage"] = usage
                    provider.calls[-1]["reply"] = reply

                self._send_json(
                    200,
                    {
                        "id": f"chatcmpl-test-{len(provider.calls)}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": "lyftr-mock",
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": reply},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": usage,
                    },
                )

            def _send_json(self, status: int, payload: dict[str, Any]) -> None:
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *_args: object) -> None:
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._server = None
        self._thread = None

    def reset(self) -> None:
        with self._lock:
            self.calls.clear()
            self.failures.clear()
            self.delay_seconds = 0.0
            self.reply_fn = default_reply

    def calls_for(self, key: str) -> list[dict[str, Any]]:
        with self._lock:
            return [call for call in self.calls if call["key"] == key]

    @property
    def call_count(self) -> int:
        with self._lock:
            return len(self.calls)
