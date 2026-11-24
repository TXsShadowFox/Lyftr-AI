# LYFTR AI

> **Reliable AI. Every Response.**

An intelligent conversational AI powered by automatic model failover, response
caching, and persistent conversation memory.

LYFTR AI is a full-stack reference implementation of the assignment contract:
React + TypeScript + Vite + Tailwind on the frontend, FastAPI + LiteLLM + SQLite
on the backend, with real per-key failover, LiteLLM's built-in response cache,
failure simulation, per-message metadata, and automated tests.

---

## 1. Live URLs

**Not deployed from this environment.** No hosting credentials, account
authorization, or deployment CLIs were available, and no public URL is invented.

| Service | Intended URL | Status |
|---|---|---|
| Frontend | `https://<your-project>.vercel.app` | Not deployed |
| Backend | `https://<your-service>.onrender.com` | Not deployed |

Deployment is prepared, not claimed: see
[Deployment instructions](#deployment-instructions), `render.yaml`, and
`frontend/vercel.json`. The backend must be hosted with a **persistent disk**
mounted at `/data`; an ephemeral filesystem will lose SQLite history.

> The referenced `LYFTR AI.pdf` was not present in the workspace. The complete
> functional specification in `prompt.txt` was used as the source of truth. Any
> PDF-only requirement that was not reproduced there could not be verified.

---

## 2. Run locally: with Docker and without

### With Docker

Prerequisites: Docker Engine/Desktop with Compose v2, GNU Make, and a real
provider API key (for example Gemini, OpenAI, Anthropic, or an OpenAI-compatible
gateway).

```bash
cp .env.example .env
# Edit .env: set LLM_MODEL and at least two values in LLM_API_KEYS.
make up
```

- Frontend: <http://localhost:3000>
- Backend: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>

`make up` builds both multi-stage images, creates the named volume
`lyftr-ai-data`, mounts it at `/data`, waits for the backend health check, then
starts nginx. `make down` stops the stack and **keeps** the SQLite volume.
`make clean` removes the volume and all persisted conversations.

Other commands:

```bash
make logs      # follow container logs
make ps        # container status
make build     # build images without starting
make test      # backend pytest + frontend production build
```

> **Verification status:** Docker was not installed in the build environment.
> The Compose YAML, `render.yaml` (against Render's published schema), Vercel
> JSON (against Vercel's published schema), and Makefile were validated; the
> Dockerfiles and nginx config were reviewed but could not be built or run. The
> non-Docker path below was executed end to end.

### Without Docker

#### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env            # edit with real keys
uvicorn app.main:app --reload --port 8000
```

The backend reads `backend/.env` when started from that directory. `DATABASE_URL`
must be a SQLite URL; `sqlite:///./data/app.db` is fine locally.

#### 2. Frontend

```bash
cd frontend
npm ci
npm run dev
```

Open <http://localhost:3000>. The browser calls the backend URL baked into
`VITE_API_BASE_URL` (default `http://localhost:8000`). CORS allows
`http://localhost:3000` and `http://127.0.0.1:3000` by default.

#### 3. Demo without provider credentials

A deterministic OpenAI-compatible mock provider is included for local UI and
integration work. It is **not** used by the deployed backend and is not a
substitute for real model output.

Unix/macOS, from the repository root:

```bash
# Terminal 1 — mock provider on :9999
backend/.venv/bin/python scripts/mock_llm.py

# Terminal 2 — backend pointed at the mock
cd backend
LLM_MODEL=openai/lyftr-mock \
LLM_API_BASE=http://127.0.0.1:9999/v1 \
LLM_API_KEYS=demo-key-1,demo-key-2 \
.venv/bin/python -m uvicorn app.main:app --port 8000
```

Windows PowerShell, from the repository root:

```powershell
# Terminal 1
backend\.venv\Scripts\python.exe scripts\mock_llm.py

# Terminal 2
cd backend
$env:LLM_MODEL="openai/lyftr-mock"
$env:LLM_API_BASE="http://127.0.0.1:9999/v1"
$env:LLM_API_KEYS="demo-key-1,demo-key-2"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

---

## 3. Design decisions: key fallback, caching, SQLite session storage

### Key fallback

- `LLM_API_KEYS` is a comma-separated pool. IDs are assigned deterministically:
  `key_1`, `key_2`, … in the order supplied. Duplicates are preserved.
- Every request starts at `key_1`. `LLMService` calls
  `litellm.completion(..., api_key=<key>)` with `max_retries=0` and
  `num_retries=0`, so the SDK cannot silently retry the same key. Failover is
  owned by our bounded loop.
- A provider failure (429, quota exhaustion, 401/403, timeout, transport error,
  or any 5xx including 500/502/503) moves to the next key. An empty successful
  response also fails over. The request succeeds on the first usable reply.
- Metadata is derived from what actually happened:
  - `key_id` is the key that produced the response, or `null` on a cache hit.
  - `fallback_attempts` is the number of failed keys before success, or `0` on
    a cache hit.
- When the pool is exhausted the API returns HTTP 503 with exactly
  `{"detail":"all providers unavailable"}`. Nothing is written to SQLite.
- Provider stack traces, URLs, and key values are never returned. Logs contain
  key IDs only (`key_1`), never secret values.

### Failure simulation

`X-Simulate-Failure` is parsed only when `ENABLE_FAILURE_SIMULATION=true`.
Supported forms:

```text
key_1=429
key_1=429,key_2=500
*=429
```

Only 429, 500, 502, and 503 are accepted. Specific key rules take precedence
over `*`. Simulation is request-scoped and never mutates global key state.
Simulated requests pass `cache={"no-cache": True, "no-store": True}` to LiteLLM,
so an existing cached response cannot bypass a failure test and a failed test
cannot write cache.

### Caching

- The cache is **LiteLLM's built-in cache** (`litellm.Cache(type="local")`,
  in-memory). There is no custom dictionary cache and no Redis.
- The cache identity is the complete LiteLLM request: model, temperature, full
  system prompt, full conversation history, and the current user message.
  Session IDs are never sent to LiteLLM, so two new sessions with the same first
  message share a cache entry.
- Cache hits are detected only from LiteLLM's
  `response._hidden_params["cache_hit"]`, never from response similarity.
- A hit returns the original reply and the original token usage, with
  `resolution_source: "LLM_CACHE"`, `key_id: null`, and
  `fallback_attempts: 0`.
- `CacheService.warm_cache_hit_path()` imports LiteLLM's lazily loaded cache-hit
  modules at startup. Without it, the first cache hit took several seconds due
  to cold imports; with it, measured hits are 2–4 ms locally.
- The in-memory cache is per process and resets on restart. This is intentional
  and allowed by the specification; run one worker if cross-request cache
  sharing matters.

### SQLite session storage

- A small stdlib `sqlite3` repository is used instead of SQLAlchemy. The
  specification permits “SQLAlchemy or a clean equivalent database layer.” The
  stdlib layer avoids a native-driver issue in the build environment and keeps
  the image small.
- `messages` has the required columns: `id`, `session_id`, `role`, `content`,
  `metadata`, `created_at`. An additional `sessions` table stores the session
  system prompt and timestamps. `sessions.system_prompt` is never returned as a
  conversation message.
- User and assistant rows are written in **one transaction after a successful
  LLM call**. A failed call writes nothing. This also guarantees that a
  partially written exchange cannot exist.
- Timestamps are ISO-8601 UTC with a `Z` suffix and millisecond precision.
  Assistant metadata is stored as JSON and returned on history reads.
- WAL mode, a 5-second busy timeout, one short-lived connection per operation,
  and parameterized SQL keep the layer safe under FastAPI's threadpool.
- In Docker, `DATABASE_URL=sqlite:////data/app.db` and the named volume
  `lyftr-ai-data` is mounted at `/data`, so data survives `make down`/`make up`.

### API and UI notes

- The three required API endpoints are `GET /health`, `POST /chat`, and
  `GET /sessions/{session_id}/messages`. `GET /` (service metadata) and
  `GET /docs` (OpenAPI UI) are auxiliary routes.
- `session_id` is 1–128 characters; `message` is 1–4000 characters **after
  trimming**; invalid requests return 422.
- The frontend generates a new session ID on every page load, sends only the
  new message, reconstructs history on the server, and renders the complete
  conversation.
- Every assistant message includes `meta-source`, `meta-model`, `meta-latency`,
  `meta-input-tokens`, and `meta-output-tokens` test IDs, plus key and fallback
  details. API keys are never sent to the browser.
- The UI uses a near-black canvas, hairline borders, Inter for reading,
  JetBrains Mono for labels and metadata, and a single blue accent, adapted from
  the OpenCode visual language without using OpenCode assets or copy.

---

## 4. Verification: how to see failover, cache hits and per-message token usage

### Automated tests

```bash
cd backend
python -m pytest -q
```

Verified result in this workspace: **91 passed** (real LiteLLM client, real
in-process cache, real failover loop, local deterministic HTTP provider). The
suite covers all 24 required categories: health, valid chat, missing session,
empty message, >4000 characters, malformed JSON, unknown session, multi-turn
memory, isolation, persistence, cache miss/hit/identity/different message/
changed history/changed system prompt, per-request tokens, simulated 429/500,
all keys failing, failed requests not saved, fallback counts, metadata, secret
exposure, and CORS.

```bash
cd frontend
npm run build          # TypeScript typecheck + Vite production build
```

Verified result: build succeeds. A local Playwright check also rendered desktop,
tablet, and mobile viewports with no horizontal overflow; every required test ID
appeared in the appropriate state. See `docs/VERIFICATION.md` for the exact
commands and observations.

### See key failover

With the backend running and `ENABLE_FAILURE_SIMULATION=true`:

```bash
curl -s http://localhost:8000/health

curl -s -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Simulate-Failure: key_1=429' \
  -d '{"session_id":"s-failover","message":"What is the capital of France?"}'
```

Expected: HTTP 200, `metadata.key_id = "key_2"`,
`metadata.fallback_attempts = 1`, and a real reply.

```bash
curl -s -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Simulate-Failure: *=429' \
  -d '{"session_id":"s-failover-down","message":"hello"}'
```

Expected: HTTP 503 with exactly `{"detail":"all providers unavailable"}`, and
`GET /sessions/s-failover-down/messages` returns 404 — the failed request was
not persisted. Remove the header and send another request; `key_1` is used
again, proving simulation is request-scoped.

### See a cache hit

1. In a fresh browser session, ask “What is the capital of France?”. Metadata
   shows `LIVE_INFERENCE`, a key ID, and token counts.
2. Click **New** (or reload) to create a new session ID.
3. Ask the exact same first question. Metadata shows `LLM_CACHE`, `key_id` is
   null, `fallback_attempts` is 0, the reply is identical, and the input/output
   token counts are the original stored usage. Local probes measured 4 ms
   cached versus 55–139 ms live; the automated suite also asserts that the
   cached path is faster.
4. Change the message, history, or system prompt and repeat; it is a cache miss.
   Session ID alone is never the cache key.

### See per-message token usage

Every assistant response carries its own `input_tokens` and `output_tokens`
from LiteLLM's usage object. They are never accumulated conversation totals.
The UI renders them as `IN` / `OUT` in the metadata strip inside each
`assistant-message` container; history reads preserve the same values.

### Required frontend test IDs

Always present in the DOM:

- `chat-input`, `send-button`
- `system-prompt-input` (in the sidebar; on mobile, inside the slide-over)

Present inside each rendered assistant message after a reply:

- `assistant-message` (one per assistant turn)
- `meta-source`, `meta-model`, `meta-latency`,
  `meta-input-tokens`, `meta-output-tokens`

### Visual QA

The optional script `frontend/scripts/visual-check.cjs` uses Playwright to
capture desktop, tablet, mobile, cache-hit, and error states, and to measure
horizontal overflow. Playwright is a local QA tool only and is not part of the
production dependency set.

```bash
cd frontend
npm install --no-save playwright
npx playwright install chromium
node scripts/visual-check.cjs
```

Screenshots are written to `screenshots/` (gitignored). They were reviewed
during development; the final layout has no horizontal overflow at 1440×900,
768×1024, or 390×844.

---

## 5. Setup Used: your editor and AI tools

- **Editor / agent harness:** OpenCode coding agent on Windows.
- **AI model:** DeepSeek V4.1 Flash Free, as configured for this session.
- **Reference inspection:** `https://opencode.ai/` HTML and shipped CSS were
  fetched and inspected for tokens and layout. Browser screenshot tooling was
  unavailable during the initial inspection; Playwright was installed later for
  local visual verification.
- **AI assistance disclosure:** the application code, tests, Docker
  configuration, and documentation were generated with AI assistance. Every
  claim in this README is based on a command that was actually run in this
  workspace, except the items explicitly marked unverified (Docker execution,
  public deployment, real-provider inference, and the absent PDF).
- **Verification tools:** Pytest 8 / HTTPX TestClient, real LiteLLM 1.110.3,
  local HTTP provider, Vite 7 / TypeScript 5, Playwright Chromium for local
  visual checks.
- No real provider API keys were available in this environment. Tests exercise
  the real LiteLLM request path against a deterministic local OpenAI-compatible
  provider; they do **not** prove a specific external provider's availability.

---

## 6. Bonus features (if any): what you added beyond the requirements and why

- **Local OpenAI-compatible mock provider** (`scripts/mock_llm.py`) so the UI,
  LiteLLM cache, failover, token accounting, and SQLite memory can be exercised
  end to end without credentials. It is clearly separated from production.
- **System prompt editor** in the sidebar, with explicit clear semantics and a
  `system-prompt-input` test ID.
- **Startup cache-path warmup** to make the first cache hit fast instead of
  paying LiteLLM's lazy-import cost on the user's first repeated question.
- **Health polling and degraded/offline states** in the UI, with readable
  connection, key-count, and cache status.
- **Retry action for failed requests** that re-sends the failed text without
  pretending the unsaved turn is part of history.
- **Session copy / new session controls**, keyboard-first composer
  (Enter sends, Shift+Enter adds a line), focus-visible states, and an error
  boundary so an unexpected render error never yields a blank screen.
- **Production Docker details:** multi-stage images, non-root backend runtime,
  nginx SPA fallback and immutable asset caching, health checks, named volume.
- **Playwright visual-check script** for repeatable desktop/tablet/mobile
  screenshots and overflow checks.

---

## Architecture overview

```text
Browser (React/Vite/Tailwind)
        │  POST /chat {session_id, message, system_prompt?}
        ▼
FastAPI route ──► ChatService
                    │ 1. load session prompt + full history from SQLite
                    │ 2. build [system?, ...history, current user message]
                    │ 3. LLMService failover loop
                    │ 4. persist both messages atomically on success
                    ▼
              LiteLLM (real provider call or local mock)
                    │ built-in in-memory response cache
                    ▼
              Provider key 1 → key 2 → … → 503
```

```text
backend/
  app/
    main.py                 app factory, lifespan, CORS
    config.py               env settings, key parsing, SQLite validation
    database.py             stdlib sqlite3 schema/repository
    models.py               typed rows
    schemas.py              exact Pydantic contracts
    routes/
      health.py
      chat.py
      sessions.py
    services/
      chat_service.py       history/prompt orchestration + persistence
      llm_service.py        LiteLLM calls, failover, cache metadata, tokens
      cache_service.py      LiteLLM cache setup + warmup
      failover_service.py   header parsing + error classification
  tests/                    pytest suite + deterministic provider
  requirements.txt
  Dockerfile
frontend/
  src/
    App.tsx
    components/             Sidebar, TopBar, EmptyState, MessageList, Composer…
    hooks/useChat.ts
    hooks/useHealth.ts
    lib/api.ts
    types.ts
  Dockerfile
  nginx.conf
  scripts/visual-check.cjs
docker-compose.yml
Makefile
.env.example
render.yaml
frontend/vercel.json
```

## API examples

```bash
# Health
curl -s http://localhost:8000/health
# {"status":"ok","keys_configured":2,"cache_enabled":true}

# Chat
curl -s -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "s-7f3a",
    "message": "What is the capital of France?",
    "system_prompt": "You are a helpful assistant."
  }'

# History
curl -s http://localhost:8000/sessions/s-7f3a/messages

# Unknown session
curl -s -o /dev/null -w '%{http_code}\n' \
  http://localhost:8000/sessions/s-unknown/messages
# 404
```

Response shape:

```json
{
  "session_id": "s-7f3a",
  "reply": "The capital of France is Paris.",
  "metadata": {
    "resolution_source": "LIVE_INFERENCE",
    "model": "gemini/gemini-3.5-flash-lite",
    "latency_ms": 812,
    "input_tokens": 42,
    "output_tokens": 9,
    "key_id": "key_1",
    "fallback_attempts": 0
  }
}
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `LLM_API_KEYS` | yes | Comma-separated provider keys; at least two for `/health` to be ready. Use keys with independent quotas (Gemini limits are per project, not per key). |
| `LLM_MODEL` | yes | LiteLLM model string, e.g. `gemini/gemini-3.5-flash-lite`. |
| `LLM_API_BASE` | no | OpenAI-compatible gateway or local mock base URL. |
| `DATABASE_URL` | yes | SQLite URL. Docker uses `sqlite:////data/app.db`. |
| `ALLOWED_ORIGINS` | yes | Comma-separated frontend origins for CORS. |
| `ENABLE_FAILURE_SIMULATION` | yes | `true` on the evaluated deployment; `false` disables the header entirely. |
| `CACHE_ENABLED` | no | Defaults to `true`; `/health` is not ready when false. |
| `CACHE_TTL_SECONDS` | no | Optional LiteLLM cache TTL; unset means no expiry. |
| `LLM_TEMPERATURE` | no | Defaults to `0.7`. |
| `LLM_REQUEST_TIMEOUT` | no | Seconds; default `60`. |
| `LLM_NUM_RETRIES` | no | Default `0`; failover is handled by the key loop. |
| `VITE_API_BASE_URL` | frontend | Build-time browser URL of the backend. |

Never commit `.env`. Only `.env.example` belongs in Git.

## Test commands

```bash
# Backend: 91 tests
cd backend
pip install -r requirements-dev.txt   # once, includes runtime + pytest
python -m pytest -q

# Frontend: typecheck + production build
cd frontend
npm run build

# Both, once Python and Node dependencies are installed
make test
```

## Deployment instructions

### Backend — Render (persistent disk)

1. Push the repository to GitHub. If this workspace is not already a Git
   repository, run `git init`, commit, and add the remote first.
2. In Render, choose **New > Blueprint** and select the repository. The included
   `render.yaml` creates a Docker web service with a 1 GB persistent disk mounted
   at `/data` and sets `DATABASE_URL=sqlite:////data/app.db`.
3. Use a paid instance type: Render's free tier does not support persistent
   disks, and SQLite history would be lost on every restart. The blueprint
   selects the 2 GB (`1c-2g`) plan for LiteLLM headroom; adjust only after
   checking memory.
4. Fill the values marked `sync: false`:
   - `LLM_MODEL`, `LLM_API_KEYS` (at least two)
   - `ALLOWED_ORIGINS=https://<your-frontend-domain>`
   - add `LLM_API_BASE` manually if using an OpenAI-compatible gateway
   - `ENABLE_FAILURE_SIMULATION=true` and `CACHE_ENABLED=true` are preset
5. Deploy and verify `GET https://<backend>/health` returns 200 with
   `keys_configured` equal to the real number of keys. The container honors
   Render's injected `PORT`.

### Frontend — Vercel

1. Import the repository and set the project root to `frontend`.
2. Build command `npm run build`, output directory `dist`.
3. Set `VITE_API_BASE_URL=https://<your-backend-domain>` in the Vercel project
   (it is baked in at build time; redeploy after changing it).
4. Deploy. Then add the Vercel origin to the backend's `ALLOWED_ORIGINS` and
   redeploy/restart the backend.
5. Verify from the deployed browser: chat, history, cache hit, and failover.

No public deployment was performed here because no credentials were available.
Do not treat the placeholder URLs above as live.

### Post-deployment checks

```bash
curl -s https://<backend>/health
curl -s -X POST https://<backend>/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"s-prod-check","message":"hello"}'
curl -s https://<backend>/sessions/s-prod-check/messages
curl -s -X POST https://<backend>/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Simulate-Failure: key_1=429' \
  -d '{"session_id":"s-prod-failover","message":"hello"}'
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/health` 503, `keys_configured < 2` | Missing or blank keys | Set two comma-separated values in `LLM_API_KEYS`. |
| `/health` 503, `cache disabled` | `CACHE_ENABLED=false` or cache init failed | Set `CACHE_ENABLED=true`; inspect startup logs for `cache_configuration_failed`. |
| Chat returns 503 `all providers unavailable` | All keys failed, invalid model, bad base URL, or simulation header | Check provider credentials/model; remove `X-Simulate-Failure`; inspect logs for key IDs only. |
| Chat logs 401/403 from a provider | Invalid or revoked key | Replace the key; failover tries the remaining keys. The API returns 503 only after the whole pool fails. |
| Cache never hits | Message/history/system prompt differs, process restarted, or multiple workers | Replay the exact same first message in a new session; keep one worker for the in-memory cache. |
| First cache hit feels slow | Cache-hit import path not warmed | Keep `CacheService.warm_cache_hit_path()` in the lifespan; do not remove it. |
| SQLite history disappears after restart | Container filesystem is ephemeral or volume not mounted | Use `DATABASE_URL=sqlite:////data/app.db` and mount the named volume at `/data`. |
| CORS error in browser | Frontend origin not in `ALLOWED_ORIGINS` | Set the exact scheme+host+port, e.g. `https://app.example.com`; restart backend. |
| Frontend calls wrong backend | `VITE_API_BASE_URL` was not set at build time | Rebuild/redeploy the frontend after setting it. |
| Docker not available | Local environment lacks Docker | Use the non-Docker instructions; the backend and frontend run independently. |

## Known limitations and honest status

- **Real provider inference was not executed.** No real API keys were available.
  Automated tests use the real LiteLLM client against a deterministic local
  OpenAI-compatible HTTP provider. This proves failover, cache, token, and
  persistence behavior, but not any specific external provider's uptime.
- **Docker was not executed.** `docker` is not installed in the build
  environment. The Compose YAML, `render.yaml` (against Render's published
  schema), Vercel JSON (against Vercel's published schema), and Makefile were
  validated; the Dockerfiles and nginx config were reviewed, but nothing
  containerized was built or run here.
- **No public deployment.** No Vercel/Render/Railway/Fly/Netlify credentials or
  CLIs were available. No URL is claimed.
- **The PDF was absent.** `prompt.txt` was the authoritative functional
  specification; PDF-only requirements could not be checked.
- The in-memory LiteLLM cache is per process and resets on restart. This is
  allowed by the specification but matters if you scale to multiple workers or
  replicas.
- There is no authentication, per-user authorization, or rate limiting. The
  assignment does not require them; session IDs are client-generated and should
  not be treated as access control.
- Replies are rendered as plain text, not Markdown. This avoids an extra
  renderer and XSS surface; the assignment does not require Markdown.
- The local mock provider is deterministic and is not a real language model.

## Demo script (2–3 minutes)

1. **0:00–0:20 — Health and empty state.** Open the frontend. Point out the
   LYFTR AI branding, `ONLINE`, `2 KEYS`, `CACHE ON`, and the new session ID.
2. **0:20–0:50 — Live inference.** Ask “What is the capital of France?”. Show
   the assistant block, the blue live rail, and metadata: `LIVE_INFERENCE`,
   model, latency, `IN`/`OUT` tokens, `key_1`, `fallbacks 0`.
3. **0:50–1:20 — Cache hit.** Click **New** and ask the same first question.
   Show the green rail, `LLM_CACHE`, `key_id` null, `fallbacks 0`, identical
   reply, identical token counts, and the much lower latency.
4. **1:20–1:50 — Failover.** Send
   `X-Simulate-Failure: key_1=429` with curl; show HTTP 200, `key_2`, fallback
   attempts 1. Send `*=429`; show HTTP 503 exact detail and that
   `GET /sessions/.../messages` is still 404.
5. **1:50–2:15 — Memory and persistence.** Send a follow-up in the first
   session; show the backend received full history. Restart the backend, then
   call `GET /sessions/<session_id>/messages` with curl to show the exchange
   persisted in SQLite (the UI intentionally starts a new session on page load,
   so it does not restore the previous conversation).
6. **2:15–2:40 — Responsive UI.** Open the mobile viewport, show the drawer,
   system prompt editor, and composer with no horizontal overflow.

## Compliance checklist

See [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) for the requirement-by-requirement
mapping and [`docs/VERIFICATION.md`](docs/VERIFICATION.md) for commands, results,
and explicitly unverified items.
