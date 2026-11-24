# LYFTR AI — Requirements Checklist

> **Source of truth:** the referenced `LYFTR AI.pdf` was **not present** in this
> workspace. This checklist is derived from the complete functional
> specification supplied in `prompt.txt`. Any requirement that existed only in
> the missing PDF could not be verified.

## Status summary

| Area | Status | Evidence |
|---|---|---|
| Backend API, failover, caching, SQLite | Implemented and tested | 91 passing pytest tests |
| React frontend, responsive UI, test IDs | Implemented; production build and Playwright QA passed | `npm run build`, `frontend/scripts/visual-check.cjs` |
| Docker and Makefile | Implemented; not executed | Docker is not installed in this environment; YAML/Make syntax checked |
| Public deployment | Not performed | No hosting credentials/CLIs or real provider keys available |
| Real external provider inference | Not performed | No real API keys; tests use the real LiteLLM client against a local provider |

Detailed commands and raw results are in [`VERIFICATION.md`](VERIFICATION.md).

---

## 1. Public API contract

| # | Requirement | Implementation | Verification |
|---|---|---|---|
| 1.1 | `GET /health` returns 200 only when the app is up, SQLite is reachable, the key pool has at least two keys, and the cache is enabled | `app/routes/health.py`; returns 503 with reasons otherwise | `tests/test_health.py` |
| 1.2 | Health response contains `status`, actual `keys_configured`, and `cache_enabled` | `HealthResponse` in `app/schemas.py` | `tests/test_health.py` |
| 1.3 | `POST /chat` accepts required `session_id`, required `message`, optional `system_prompt` | `ChatRequest` | `tests/test_chat_sessions.py`, `tests/test_validation.py` |
| 1.4 | `session_id` is 1–128 chars; `message` is 1–4000 chars after trimming; invalid requests return 422 | Pydantic validators | `tests/test_validation.py` |
| 1.5 | Unknown session IDs start a new session | `ChatService` upserts `sessions` | `tests/test_chat_sessions.py` |
| 1.6 | Response shape is `{session_id, reply, metadata{...}}` | `ChatResponse` / `ChatMetadata` | `tests/test_metadata_tokens.py` |
| 1.7 | `resolution_source` is exactly `LIVE_INFERENCE` or `LLM_CACHE` | `Literal` type; value comes from LiteLLM's cache flag | `tests/test_cache.py` |
| 1.8 | `model` reports the configured/actual LiteLLM model | `LLMResult.model` | `tests/test_metadata_tokens.py` |
| 1.9 | `latency_ms` is an integer measured server-side | `time.perf_counter()` around the failover loop | `tests/test_metadata_tokens.py`, `tests/test_cache.py` |
| 1.10 | `input_tokens` / `output_tokens` are per-request, never conversation totals | Extracted from each LiteLLM response's usage object | `tests/test_metadata_tokens.py` |
| 1.11 | `key_id` is the successful key, or `null` on a cache hit | `LLMResult` | `tests/test_failover.py`, `tests/test_cache.py` |
| 1.12 | `fallback_attempts` counts failed keys before success; 0 on a cache hit | Bounded failover loop | `tests/test_failover.py`, `tests/test_cache.py` |
| 1.13 | `GET /sessions/{session_id}/messages` returns chronological messages with assistant metadata | `ChatService.get_messages`, ordered by row id | `tests/test_chat_sessions.py`, `tests/test_metadata_tokens.py` |
| 1.14 | System prompts are never returned as conversation messages | Prompt lives only in `sessions.system_prompt` | `tests/test_chat_sessions.py` |
| 1.15 | Unknown session returns 404 with exactly `{"detail":"session not found"}` | `app/routes/sessions.py` | `tests/test_chat_sessions.py` |
| 1.16 | Malformed JSON returns 422 | FastAPI JSON parser | `tests/test_validation.py` |

> `GET /` (service metadata) and `/docs` (OpenAPI UI) are auxiliary routes; the
> three required API endpoints are `/health`, `/chat`, and
> `/sessions/{session_id}/messages`.

## 2. LiteLLM, key pool and failover

| # | Requirement | Implementation | Verification |
|---|---|---|---|
| 2.1 | LiteLLM is the LLM gateway | `litellm.completion` in `services/llm_service.py` | Real LiteLLM client exercised by all chat tests |
| 2.2 | At least two keys from `LLM_API_KEYS`; IDs `key_1..key_n`; no hardcoded credentials | `config.py` parses the comma list; `.env.example` has placeholders only | `tests/test_health.py`, `tests/test_config.py`, secret audit |
| 2.3 | Fail over on 429, quota exhaustion, 500/502/503 and other provider 5xx | Every provider-side exception moves to the next key | `tests/test_failover.py` (simulated and real 429/500) |
| 2.4 | Try key 1, detect failure, switch key, continue to success/exhaustion, record successful key and failure count | `LLMService.complete` | `tests/test_failover.py` |
| 2.5 | Failover actually changes `api_key`; metadata is not faked | Each attempt passes `api_key=key.value`; the mock provider records it | `tests/test_failover.py` |
| 2.6 | All providers failing returns 503 with exactly `{"detail":"all providers unavailable"}` | `AllProvidersUnavailableError` handler | `tests/test_failover.py` |
| 2.7 | Failed requests are not written to SQLite | Persistence happens only after a successful call | `tests/test_failover.py`, `tests/test_chat_sessions.py` |
| 2.8 | Provider stack traces and API secrets are never exposed | Generic 503; structured error names/status only in logs | `tests/test_security.py` |

## 3. Failure simulation

| # | Requirement | Implementation | Verification |
|---|---|---|---|
| 3.1 | `X-Simulate-Failure` supports `key_1=429`, `key_1=429,key_2=500`, `*=429` | `parse_failure_header` | `tests/test_failover.py`, `tests/test_config.py` |
| 3.2 | Only 429/500/502/503 are accepted | Status whitelist | `tests/test_config.py`, `tests/test_failover.py` |
| 3.3 | Simulation only works when `ENABLE_FAILURE_SIMULATION=true` | Checked before parsing | `tests/test_failover.py` |
| 3.4 | Test 1: `key_1=429` returns 200 with `key_2`, `fallback_attempts=1`, real reply | Failover loop | `tests/test_failover.py` |
| 3.5 | Test 2: `key_1=500` returns 200 with `key_2`, real reply | Failover loop | `tests/test_failover.py` |
| 3.6 | Test 3: `*=429` returns exact 503 and creates no history | Failure raised before persistence | `tests/test_failover.py` |
| 3.7 | Simulation affects only the current request | Request-scoped parse; no key state is mutated | `tests/test_failover.py` |
| 3.8 | An existing cache entry cannot bypass failure tests | Simulated requests use `cache={"no-cache": true, "no-store": true}` | `tests/test_failover.py` |
| 3.9 | A failed request cannot populate the cache | `no-store` on simulated requests | `tests/test_failover.py` |

## 4. Caching

| # | Requirement | Implementation | Verification |
|---|---|---|---|
| 4.1 | LiteLLM's built-in cache is used, not a custom dictionary | `litellm.Cache(type="local")` in `services/cache_service.py` | `tests/test_cache.py` |
| 4.2 | Allowed backend: in-memory or disk; no Redis | In-memory LiteLLM cache only; no external services | Config review, integration tests |
| 4.3 | Cache identity depends on model, full system prompt, full history, current message | Full message list goes to LiteLLM; session ID is never included | `tests/test_cache.py` |
| 4.4 | First request is a miss and returns `LIVE_INFERENCE` | LiteLLM miss flag false | `tests/test_cache.py` |
| 4.5 | Same first message in a different session is a hit with identical text/tokens, `key_id=null`, `fallback_attempts=0` | Cache-hit mapping from `_hidden_params` | `tests/test_cache.py` |
| 4.6 | A different message never reuses an unrelated response | Full messages are part of the cache key | `tests/test_cache.py` |
| 4.7 | Changed history changes cache identity | History is sent with every request | `tests/test_cache.py` |
| 4.8 | Changed system prompt changes cache identity | System message is sent with every request | `tests/test_cache.py` |
| 4.9 | Cache hits are faster than live inference | Measured server-side latency; startup warmup removes lazy-import cost | `tests/test_cache.py` |
| 4.10 | Cache metadata reflects actual LiteLLM reuse, not response similarity | `response._hidden_params["cache_hit"] is True` | `tests/test_cache.py` |

## 5. SQLite session storage

| # | Requirement | Implementation | Verification |
|---|---|---|---|
| 5.1 | SQLite only; Docker URL is `sqlite:////data/app.db` | Validator rejects non-SQLite URLs; Compose sets the absolute path | `tests/test_config.py`, `docker-compose.yml` |
| 5.2 | Database lives on a persistent Docker volume mounted at `/data` | Named volume `lyftr-ai-data` mounted at `/data` | `docker-compose.yml`; not executed |
| 5.3 | Schema is created automatically at startup | `Database.init()` in the lifespan | `tests/test_database.py` |
| 5.4 | `messages` has `id`, `session_id`, `role`, `content`, `metadata`, `created_at` | `app/database.py` `SCHEMA` | `tests/test_database.py` |
| 5.5 | Store both roles, session association, chronological order, JSON metadata, ISO-8601 timestamps | `save_exchange` writes both rows in one transaction; UTC `Z` timestamps | `tests/test_database.py`, `tests/test_metadata_tokens.py` |
| 5.6 | Conversations are isolated by session | All reads filter by `session_id` | `tests/test_chat_sessions.py` |
| 5.7 | Data survives restarts/container restarts | File-backed SQLite; app-restart test passes; Docker volume configured | `tests/test_chat_sessions.py`, `tests/test_database.py`; container restart not executed |
| 5.8 | Only successful user/assistant exchanges are committed | One transaction after the LLM succeeds | `tests/test_failover.py` |

Additional `sessions` table stores the session-level system prompt and creation/
update timestamps. `messages.role` has a `CHECK` constraint. WAL mode, a busy
timeout, parameterized SQL, and one short-lived connection per operation are
used.

## 6. Frontend

| # | Requirement | Implementation | Verification |
|---|---|---|---|
| 6.1 | React + TypeScript + Vite + Tailwind + Lucide React | `frontend/package.json` | `npm run build` |
| 6.2 | OpenCode-inspired design: dark canvas, mono accents, hairlines, restrained palette, precise spacing | `tailwind.config.ts`, `index.css`, components; tokens documented in `docs/DESIGN.md` | Playwright screenshots reviewed |
| 6.3 | LYFTR AI branding, subtitle, and product description | Sidebar, top bar, empty state, page metadata | Playwright/DOM review |
| 6.4 | Chat area, distinguished roles, composer, send, loading, empty state, errors, smooth scrolling | `MessageList`, `Composer`, `EmptyState`, `ErrorBanner`, `App` | Playwright QA |
| 6.5 | Per-response metadata: source, model, latency, input/output tokens, plus key/fallbacks | `AssistantMeta` inside each assistant article | Playwright DOM assertions |
| 6.6 | Optional session-level system prompt editor | `Sidebar`; mobile slide-over keeps it accessible | Playwright (drawer visible) |
| 6.7 | Responsive desktop/tablet/mobile with no horizontal overflow | Tailwind breakpoints; 1440×900, 768×1024, 390×844 checked | `frontend/scripts/visual-check.cjs` |
| 6.8 | New session ID on every page load | `useState(createSessionId)` | Source |
| 6.9 | Sends only the new message; clears input; displays complete multi-turn conversation | `useChat.send` and local message state | Playwright chat run |
| 6.10 | Prevents accidental duplicate submissions | `sendingRef`, disabled composer/button | Source |
| 6.11 | Readable 422/503 errors; never a blank screen | `describeApiError`, `ErrorBanner`, `ErrorBoundary` | Playwright 503 state; build |
| 6.12 | Backend URL from environment | `VITE_API_BASE_URL` at build time | Build/env review |
| 6.13 | Exact test IDs: `chat-input`, `send-button`, `assistant-message`, `meta-source`, `meta-model`, `meta-latency`, `meta-input-tokens`, `meta-output-tokens`, `system-prompt-input` | Components | Playwright DOM dump |
| 6.14 | Accessibility and keyboard usability | Labels, aria-live, focus-visible styles, Escape closes drawer, Enter sends, Shift+Enter newline | Source + Playwright |

## 7. Docker and developer experience

| # | Requirement | Implementation | Verification |
|---|---|---|---|
| 7.1 | Multi-stage Dockerfiles for both services | `backend/Dockerfile`, `frontend/Dockerfile` | Static review; Docker unavailable |
| 7.2 | `make up` / `make down`; frontend :3000, backend :8000 | `Makefile`, `docker-compose.yml` | Make syntax/help executed; containers not run |
| 7.3 | Root Compose file, named volume at `/data`, env config, networking, CORS, health checks | `docker-compose.yml`, CORS in `app/main.py` | YAML parsed; runtime not executed |
| 7.4 | No credentials committed | `.gitignore` excludes `.env*` except `.env.example`; scan for secrets | Audit + `tests/test_security.py` |
| 7.5 | Backend honors host-injected `PORT` where required | Docker `CMD` uses `${PORT:-8000}` | Render config review |

## 8. Required automated tests

All 24 required categories are covered by the 91-test suite.

| # | Required test | Covering file(s) |
|---|---|---|
| 8.1 | Health endpoint | `test_health.py` |
| 8.2 | Valid chat request | `test_chat_sessions.py` |
| 8.3 | Missing session ID | `test_validation.py` |
| 8.4 | Empty message | `test_validation.py` |
| 8.5 | Message over 4000 characters | `test_validation.py` |
| 8.6 | Malformed JSON | `test_validation.py` |
| 8.7 | Unknown session | `test_chat_sessions.py` |
| 8.8 | Multi-turn memory | `test_chat_sessions.py` |
| 8.9 | Session isolation | `test_chat_sessions.py` |
| 8.10 | SQLite persistence | `test_chat_sessions.py`, `test_database.py` |
| 8.11 | Cache miss | `test_cache.py` |
| 8.12 | Cache hit | `test_cache.py` |
| 8.13 | Cache identity across sessions | `test_cache.py` |
| 8.14 | Different-message cache miss | `test_cache.py` |
| 8.15 | Changed-history cache miss | `test_cache.py` |
| 8.16 | Accurate per-request tokens | `test_metadata_tokens.py` |
| 8.17 | Key 1 simulated 429 | `test_failover.py` |
| 8.18 | Key 1 simulated 500 | `test_failover.py` |
| 8.19 | All keys simulated failure | `test_failover.py` |
| 8.20 | Failed requests not saved | `test_failover.py` |
| 8.21 | Correct fallback attempts | `test_failover.py` |
| 8.22 | Correct metadata | `test_metadata_tokens.py` |
| 8.23 | No secret exposure | `test_security.py` |
| 8.24 | CORS behavior | `test_security.py` |

Additional coverage: config parsing, SQLite unit behavior, real-provider-path
429/500 failover through LiteLLM, cache bypass on failure, cache speed, system
prompt semantics, timestamps/metadata JSON, SQL-injection parameterization, log
redaction, and preflight/CORS.

## 9. Deployment

| # | Requirement | Status |
|---|---|---|
| 9.1 | Public frontend and backend | **Blocked.** No hosting credentials, authorization, or CLIs were available. No URL is claimed. |
| 9.2 | Persistent SQLite volume on the backend host | `render.yaml` defines a paid web service with a disk mounted at `/data`. Requires manual account setup. |
| 9.3 | Configure env vars/CORS and verify the public stack | Steps documented in `README.md`; not executed without credentials. |

## 10. Documentation

| # | Requirement | Implementation |
|---|---|---|
| 10.1 | README with the six exact required sections | `README.md` sections 1–6 |
| 10.2 | Architecture, installation, env setup, Docker, API examples, tests, deployment, troubleshooting, demo script | `README.md`, `docs/VERIFICATION.md`, `docs/DESIGN.md` |
| 10.3 | Honest AI-tool disclosure and no real keys | `README.md` section 5; `.env.example` placeholders only |

## 11. Explicitly unverified items

These are disclosed rather than claimed:

1. **Public deployment** — no Vercel/Render/Railway/Fly/Netlify account,
   credentials, or CLI was available.
2. **Docker execution** — `docker` is not installed here. Dockerfiles, Compose,
   nginx, and Makefile were authored and statically/syntax checked only.
3. **Real external provider inference** — no real provider API keys were
   available. The suite exercises the real LiteLLM client against a local
   deterministic OpenAI-compatible HTTP provider. This proves the integration,
   failover, cache, token, and persistence paths but not any specific external
   provider's availability.
4. **The missing PDF** — `LYFTR AI.pdf` was absent; `prompt.txt` was used as the
   functional specification.
5. **Container-level volume persistence** — SQLite persistence across app
   restarts is tested, but not across a real container restart.
