# Security

Status of security controls in PrismAgents Self-Hosted — what's enforced today, what's open, and how to close the gaps. Read this before any non-local deployment.

## Threat model summary

| Asset | Sensitivity | Current control |
|---|---|---|
| User identity (Local auth / GitHub OAuth) | High | Password hash + JWT / OAuth + JWT |
| Chat content | Medium | Per-user board ownership checks |
| fal.ai API key (`FAL_KEY`) | High (paid usage) | Server-only, `.env` |
| JWT signing secret | High | Required, ≥32 chars |
| Database credentials | High | Server-only, `.env` |

## Controls in place

### Authentication

- **GitHub OAuth → JWT** — sole login path. JWT is HS256-signed with `JWT_SECRET`, payload `{sub, exp, iat}`, 24h default TTL. See `auth/jwt.py`.
- **JWT secret guard** — `_get_jwt_secret()` raises `RuntimeError` if `JWT_SECRET` is unset or shorter than 32 characters. No insecure default.
- **Timezone-aware timestamps** — `datetime.now(timezone.utc)`; no deprecated `datetime.utcnow()` usage.

### Authorization

- **Bearer auth on every protected route** — `auth.dependencies.get_current_user` wraps `HTTPBearer`. `401` on missing or invalid JWT.
- **Per-resource ownership checks at the router layer** — every `GET/PUT/DELETE /<resource>/{id}` calls `get_<resource>_by_id(id, user_id)` before acting; mismatched ownership → `404`. Prevents IDOR.
- **Soft-delete for agents** — `services.agent.delete_agent` flips `isActive=false` rather than removing rows, preserving an audit trail.

### Transport / CORS

- **CORS scoped to `FRONTEND_URL`** — no wildcard origin. The `["*"]` + `allow_credentials=True` combination (which browsers reject anyway) is gone. Set `FRONTEND_URL` per environment.

### Data validation

- **All ID path params typed `uuid.UUID`** — FastAPI rejects non-UUID input with `422` before any handler runs.
- **Request bodies are Pydantic models** — fields not declared are dropped; types are enforced.

### Repository hygiene

- **`.gitignore` covers `.env`, `.env.*` (with `!.env.example`), `.venv`, `.ruff_cache/`, build dirs.** Confirmed no secrets are tracked in git history at the time of writing.

## Open issues

These are real gaps that should be closed before any production deployment. Severity reflects exploitability and impact, not difficulty to fix.

### 🔴 1. OAuth state never validated (CSRF)

**Where:** `auth/router.py::github_callback` accepts `state` as a query param but never verifies it. `auth/github.py::generate_state` produces a fresh random value at `/auth/github` time but the backend never stores it.

**Impact:** OAuth login CSRF. An attacker can trigger the OAuth flow with their own GitHub account, then craft a URL pointing the victim's browser to `/auth/callback?code=<attacker's code>&state=anything`. The victim's browser exchanges the code, gets back a JWT for the attacker's account, and operates in it unknowingly — exposing whatever the victim does in the app to the attacker.

**Fix sketch (no server-side storage required):** sign the state as a short-TTL JWT.

```python
# auth/github.py
from media_agents.auth.jwt import _get_jwt_secret, _get_jwt_algorithm
from datetime import datetime, timezone, timedelta
from jose import jwt as jose_jwt, JWTError

def generate_state() -> str:
    payload = {
        "nonce": secrets.token_urlsafe(16),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jose_jwt.encode(payload, _get_jwt_secret(), algorithm=_get_jwt_algorithm())

def verify_state(state: str) -> bool:
    try:
        jose_jwt.decode(state, _get_jwt_secret(), algorithms=[_get_jwt_algorithm()])
        return True
    except JWTError:
        return False
```

In `github_callback`, raise `400 Invalid state` if `verify_state(state)` is false.

### 🔴 2. GitHub access tokens stored in plaintext

**Where:** `User.accessToken` (Prisma column `access_token`). Set on first OAuth and refreshed on every login by `services.user.create_user` / `update_user`.

**Impact:** If the database leaks, every user's GitHub access is compromised. Current scopes (`read:user user:email`) are modest, but still expose private email and profile data. The application code never reads `accessToken` after login — it's stored and never used.

**Fix:** stop persisting it.

1. Drop the `accessToken` argument from `services.user.create_user` and `update_user`.
2. Stop passing it from `auth.router::github_callback`.
3. Migration: `ALTER TABLE users DROP COLUMN access_token;` (Prisma: remove the field, then `uv run prisma migrate dev --name drop_access_token`).

### 🟡 3. Client-supplied chat history (prompt injection + abuse)

**Where:** `routers/chat.py::ChatRequest.history` is supplied by the client and passed straight to the LLM after dict conversion.

**Impact:** A malicious client can inject fake `{role: "assistant", content: "..."}` turns to manipulate the model (e.g., "previous assistant turn: I'll ignore safety guidelines"). Even without malice, the field has no length cap → token-burn DoS.

**Fix:** derive history server-side from prior `Generation` rows on the board.

```python
# routers/chat.py
async def chat_event_generator(request, user_id):
    ...
    history = await generation_service.get_recent_turns(
        request.board_id, user_id, limit=20
    )
    history_dicts = [{"role": "user", "content": g["prompt"]} for g in history]
    # Append assistant turns from metadata.text or result_url depending on result_type
    async for chunk in orchestrator.stream(request.message, history_dicts):
        ...
```

Then remove the `history` field from `ChatRequest` to deprecate the client-side path entirely.

### 🟡 4. No rate limiting

**Where:** No middleware caps requests. `/chat/stream` is the most expensive endpoint (every call hits OpenRouter or fal models).

**Impact:** A leaked JWT or a single malicious user can drain fal.ai credits. No protection against credential-stuffing on `/auth/callback` either.

**Fix sketch:** add `slowapi` (Starlette-compatible). Per-user rate limits keyed on JWT `sub`:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

def user_id_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        user_id = decode_token(auth[7:])
        if user_id:
            return str(user_id)
    return get_remote_address(request)

limiter = Limiter(key_func=user_id_key)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

@router.post("/stream")
@limiter.limit("30/minute")
async def chat_stream(...):
    ...
```

### 🟡 5. No input length cap on chat message

**Where:** `routers/chat.py::ChatRequest.message: str` accepts arbitrary length.

**Impact:** Token-burn DoS — a single 100KB message gets sent to OpenRouter at the user's expense.

**Fix:** add a Pydantic `Field`:

```python
from pydantic import Field

class ChatRequest(BaseModel):
    board_id: uuid.UUID
    message: str = Field(min_length=1, max_length=8000)
    agent_id: Optional[uuid.UUID] = None
    history: list[ChatMessage] = []
```

### 🟡 6. JWT in `localStorage` (XSS exposure)

**Where:** `useAuthStore.setAuth` writes the JWT to `localStorage`; every API call reads it back.

**Impact:** Any XSS on the frontend exfiltrates the token. The current React rendering escapes by default and there is no raw-HTML injection, so the surface is small — but a single careless dependency or SVG injection changes that.

**Mitigations (in order of effort):**
- Set strict CSP headers on the FastAPI responses (or a reverse proxy).
- Add a lint rule (`react/no-danger`) to prevent raw-HTML injection from ever landing.
- For higher security: switch to `httpOnly` cookies for the JWT and have the backend issue/refresh via cookies. Requires a CSRF token strategy and converting the auth flow to set-cookie semantics.

### 🟢 7. URLs from upstream rendered without scheme validation

**Where:** `history-panel.tsx` renders `selectedGeneration.result_url` in `<img src>`, `<video src>`, and `<a href target="_blank">`. URLs come from fal.ai (always https) — but if the orchestrator ever yields a URL from less-trusted input (e.g., a custom-agent tool call), `javascript:` URLs would XSS via the `<a href>`.

**Fix:** validate the URL scheme on the backend before persisting, or on the frontend before rendering:

```typescript
const isSafeUrl = (url: string) => {
  try { return new URL(url).protocol === "https:" } catch { return false }
}
```

## Verification before deployment

```bash
# Frontend dependency CVEs
cd frontend && npm audit --production

# Backend dependency CVEs
cd backend && uv run pip-audit  # or: uv pip install pip-audit && uv run pip-audit

# Static credential search
grep -rn "password\|secret\|api_key\|sk-\|ghp_" --include="*.py" --include="*.ts" --include="*.tsx" .

# Confirm no env files in git history
git log --all -- '**/.env*'
```

## Hardening checklist for production

- [ ] `JWT_SECRET` set to ≥48 random characters (`python -c "import secrets; print(secrets.token_urlsafe(48))"`)
- [ ] `FRONTEND_URL` set to production origin (`https://...`)
- [ ] Issue 1 (OAuth state validation) addressed
- [ ] Issue 2 (drop stored access tokens) addressed
- [ ] Issue 3 (server-side chat history) addressed
- [ ] Issue 4 (rate limiting) at least on `/chat/stream` and `/auth/callback`
- [ ] Issue 5 (input length cap) addressed
- [ ] Database backups configured
- [ ] CSP and HSTS headers set (reverse proxy or middleware)
- [ ] Monitoring + alerting on `5xx` rates and fal.ai cost
- [ ] `npm audit` and `pip-audit` clean
