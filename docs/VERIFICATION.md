# LYFTR AI — Verification Log

**Recorded:** 2026-11-24
**Environment:** Windows 11, PowerShell 7.x, Python 3.12 virtualenv,
Node.js 25.9.0, npm 11.12.1.
**Scope:** commands actually executed in this workspace. Items that could not be
executed are listed separately and are **not** claimed as verified.

---

## 1. Backend test suite

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```text
........................................................................ [ 79%]
...................                                                      [100%]
91 passed, 14 warnings in 7.73s
```

The 14 warnings are third-party LiteLLM/Pydantic `TypedDict` warnings about
`ReadOnly` qualifiers; they are not test failures or application warnings.

Test count by module:

| Module | Tests |
|---|---:|
| `tests/test_cache.py` | 7 |
| `tests/test_chat_sessions.py` | 8 |
| `tests/test_config.py` | 22 |
| `tests/test_database.py` | 4 |
| `tests/test_failover.py` | 12 |
| `tests/test_health.py` | 4 |
| `tests/test_metadata_tokens.py` | 6 |
| `tests/test_security.py` | 9 |
| `tests/test_validation.py` | 19 |
| **Total** | **91** |

The suite uses the real `litellm.completion` client against an in-process
deterministic OpenAI-compatible HTTP provider (`tests/mock_provider.py`). It
does not mock LiteLLM itself, the failover loop, the cache, or SQLite.

## 2. Frontend production build

```powershell
cd frontend
npm run build
```

Result: exit code 0. `tsc --noEmit` reported no errors, and Vite built 1,595
modules:

```text
dist/index.html                    0.76 kB  │ gzip:  0.44 kB
dist/assets/index-*.css           26.21 kB  │ gzip:  7.73 kB
dist/assets/index-*.js           253.35 kB  │ gzip: 78.00 kB
```

Fonts are bundled locally (Inter and JetBrains Mono), so the UI does not depend
on Google Fonts or another external CDN at runtime.

## 3. Live API checks against the local mock provider

The backend ran on `127.0.0.1:8000` with `ENABLE_FAILURE_SIMULATION=true`,
`LLM_MODEL=openai/lyftr-mock`, two demo keys, and the deterministic mock
provider on `127.0.0.1:9999`. No real provider key was used.

### Health

```text
GET /health -> 200
{"status":"ok","keys_configured":2,"cache_enabled":true}
```

### Cache miss, cache hit, failover, and failure persistence

A fresh message was sent under two different session IDs. Exact observed
metadata:

```json
{
  "live": {
    "resolution_source": "LIVE_INFERENCE",
    "model": "openai/lyftr-mock",
    "latency_ms": 139,
    "input_tokens": 6,
    "output_tokens": 26,
    "key_id": "key_1",
    "fallback_attempts": 0
  },
  "cache": {
    "resolution_source": "LLM_CACHE",
    "model": "openai/lyftr-mock",
    "latency_ms": 4,
    "input_tokens": 6,
    "output_tokens": 26,
    "key_id": null,
    "fallback_attempts": 0
  },
  "simulated_key_1_429": {
    "resolution_source": "LIVE_INFERENCE",
    "key_id": "key_2",
    "fallback_attempts": 1
  }
}
```

The cached reply was byte-for-byte identical to the live reply, and reused the
original token counts. A `*=429` request returned exactly:

```json
{"detail":"all providers unavailable"}
```

with HTTP 503. `GET /sessions/<that-session>/messages` then returned HTTP 404,
proving the failed exchange was not persisted.

## 4. Browser QA

Playwright Chromium was installed locally with `npm install --no-save
playwright`; it is **not** part of `package.json`. The development server and
mock-backed API were running.

```powershell
cd frontend
node scripts/visual-check.cjs
```

Observed results:

| Check | Result |
|---|---|
| Desktop 1440×900 empty state | `scrollWidth = innerWidth = 1440`; no horizontal overflow |
| Last empty-state suggestion | Fully visible above the composer |
| Required IDs on empty state | `system-prompt-input`, `chat-input`, `send-button` |
| Live reply | `LIVE_INFERENCE`, `openai/lyftr-mock`, `384 ms`, IN 6 / OUT 6, one assistant message |
| Cache replay in a new session | `LLM_CACHE`, one assistant message; sidebar source `CACHE` |
| Simulated 503 | Error alert rendered, input cleared, 0 assistant messages |
| Tablet 768×1024 | `scrollWidth = innerWidth = 768`; no horizontal overflow |
| Mobile 390×844 | `scrollWidth = innerWidth = 390`; no horizontal overflow |
| Mobile drawer | `system-prompt-input` visible; no overflow |
| Mobile chat | `LIVE_INFERENCE`; no overflow |
| Page errors | None; only the expected console 503 from the intentionally intercepted request |

Screenshots were written to `screenshots/` (gitignored): empty desktop,
live desktop, cache desktop, error desktop, empty mobile, mobile drawer, mobile
chat, and empty tablet.

The assistant metadata IDs (`meta-source`, `meta-model`, `meta-latency`,
`meta-input-tokens`, `meta-output-tokens`) were queried successfully after the
live reply, inside the `assistant-message` article.

## 5. Configuration syntax checks

```powershell
node -e "JSON.parse(require('fs').readFileSync('frontend/vercel.json','utf8'))"
# vercel.json OK

.\.venv\Scripts\python.exe -c "import yaml, pathlib; ..."
# YAML syntax OK

make help
# Makefile parsed and all documented targets listed
```

- `docker-compose.yml` parses as YAML with services `backend` and `frontend` and
  named volume `lyftr-ai-data`.
- `render.yaml` is valid against Render's published Blueprint schema
  (`https://render.com/schema/render.yaml.json`), with web service
  `lyftr-ai-api` and disk mount `/data`.
- `frontend/vercel.json` is valid against Vercel's published schema
  (`https://openapi.vercel.sh/vercel.json`) and parses as JSON.

A final re-validation with `jsonschema 4.26.0` against the live published
schemas printed:

```text
render.yaml: valid against Render published schema
frontend/vercel.json: valid against Vercel published schema
docker-compose services: ['backend', 'frontend']
compose volume: lyftr-ai-data
```

## 6. What was not verified

| Item | Reason | Current evidence |
|---|---|---|
| Docker image build / `make up` | `docker` is not installed here (`docker --version` is unavailable) | Multi-stage Dockerfiles, Compose, nginx config, and Makefile reviewed; YAML/Make syntax checked only |
| Nginx config execution | `nginx` is not installed here | Static review only |
| Container volume persistence | Requires Docker | App-level SQLite restart persistence is tested |
| Real external provider inference | No real provider API keys were available | Real LiteLLM client tested against a local OpenAI-compatible provider |
| Public deployment | No hosting credentials/authorization/CLIs | `render.yaml` and `frontend/vercel.json` are ready; README documents exact steps |
| PDF-only requirements | `LYFTR AI.pdf` was absent from the workspace | `prompt.txt` used as the functional specification |

These gaps are intentionally disclosed in the README and requirements checklist.
No public URL or external-provider success is claimed.
