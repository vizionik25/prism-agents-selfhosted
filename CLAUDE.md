# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository shape

Monorepo with two independent deployables:

- `backend/` — FastAPI + Prisma (Python client) on Python 3.12, managed with `uv`. Deployed via Docker Compose; local PostgreSQL or external (Neon).
- `frontend/` — Next.js 16 App Router + React 19 + Tailwind v4 + shadcn/ui + Zustand. Deployed via Docker Compose or Vercel; the backend only serves JSON/SSE.

**Self-Hosted Edition:** No Stripe billing, no cloud dependencies. Users supply their own `FAL_KEY`. All features unlocked with unlimited credits in self-hosted mode.

**Agent framework: PydanticAI.** Every agent in `media_agents/agents/` (the Luma orchestrator, agent-maker, research, and all specialist agents in `agents/specialist/`) is a `pydantic_ai.Agent[OrchestratorDeps, str]`. LLM calls go through a custom `pydantic_ai.models.function.FunctionModel` (`agents/fal_model.py::***`) that proxies to `fal-ai/openrouter/chat/completions` — so there is no OpenAI / OpenRouter / Anthropic SDK in the project, only `fal_client` + PydanticAI. When adding an agent, follow the PydanticAI patterns (`@agent.tool`, `@agent.instructions`, `RunContext[OrchestratorDeps]`, `agent.run(...)`) — do not bypass it by calling fal directly unless you are the chat model adapter itself.

Docs in `docs/` are authoritative for design — especially `architecture.md`, `api-reference.md`, `security.md`, and anything under `docs/specs/`.

## Commands

### Backend (run from `backend/`)

| Task | Command |
|------|---------|
| Install deps (incl. dev) | `uv sync` |
| Run API (dev) | `uv run uvicorn media_agents.main:app --host 0.0.0.0 --port 8200 --reload` |
| Regenerate Prisma client | `uv run prisma generate` (**required after any schema edit or fresh checkout**) |
| New migration | `uv run prisma migrate dev --name <slug>` |
| Apply migrations in prod | `uv run prisma migrate deploy` |
| Prisma Studio | `uv run prisma studio` |
| Full test suite | `uv run pytest` |
| Single test file | `uv run pytest tests/test_jwt.py -v` |
| Lint | `uv run ruff check .` |
| Docker Compose (full stack) | `docker compose up --build` (from repo root) |

### Frontend (run from `frontend/`)

| Task | Command |
|------|---------|
| Install deps | `npm install` |
| Dev server | `npm run dev` (port 3000) |
| Production build | `npm run build` |
| Lint | `npm run lint` |

There is no `npm test` — the frontend has no test suite.

## Big-picture architecture

### Layered backend — strict import rules

```
routers/*.py   ← FastAPI path ops. Request/response Pydantic models.
    │            Owns snake_case ↔ camelCase marshalling and _format_datetime helpers.
    ▼
services/*.py  ← The ONLY layer that imports `prisma`. Returns Prisma row dicts (camelCase).
    ▼
media_agents.prisma.prisma  (single shared instance)
```

**Rule: routers never import `prisma` directly — always go through `services/<resource>.py`.**

**Casing convention:** the Prisma Python client uses camelCase (`systemPrompt`, `createdAt`); HTTP responses use snake_case. Each router explicitly maps fields in its response model constructors. Don't try to "fix" this by unifying — it's an intentional boundary.

### Agent orchestration (`media_agents/agents/`)

HTTP-independent. Every agent is a PydanticAI `Agent` typed as `Agent[OrchestratorDeps, str]` — deps carry `user_id`, `board_id`, the active `system_prompt`, and anything else tools need via `RunContext`. Tools are declared with `@agent.tool`; dynamic system prompts with `@agent.instructions`. LLM calls flow through the custom `FunctionModel` in `fal_model.py::***` → fal's OpenRouter proxy — which is why there's no OpenAI/OpenRouter key, only `FAL_KEY`.

The adapter today calls `fal_client.run_async(...)` and returns one full `ModelResponse`, so `agent.run()` is the right call pattern. fal.ai itself supports streaming (via `fal_client.stream_async` / the streaming endpoints) — the non-streaming behavior is a property of this adapter, not of fal. The user-visible SSE stream from `routers/chat.py` is driven by the orchestrator chunking its output as `TEXT:`/`URL:`/`STATUS:` events, not by token-level LLM streaming.

Two modules touch `fal_client`:
- `agents/client.py::FalClient` — asset generation only (image/video/speech). Singleton `fal_client`.
- `agents/fal_model.py` — PydanticAI chat adapter over OpenRouter.

The **chat contract** between `orchestrator.stream()` and `routers/chat.py` is prefix-tagged string chunks:

| Prefix | SSE event | DB side-effect |
|--------|-----------|----------------|
| `TEXT:` | `message` | accumulated into `metadata.text` at end |
| `URL:` | `url` | first → `Generation.result_url`; rest → `GenerationVariant` rows |
| `STATUS:` | `status` | `update_generation(status= upper())` |
| `ERROR:` | `error` | `update_generation(status="FAILED")`, stream ends |

Touch one side of this contract and you touch the other. The orchestrator never imports HTTP; the router never imports fal.

### Slash commands

Parsed in `AgentOrchestrator._parse_command` — `/image`, `/video`, `/research`, `/create_agent`, `/help` bypass the LLM entirely (deterministic, zero token cost). Free-form input goes to the `luma_agent` PydanticAI agent with three registered tools. The active system prompt is wired via a dynamic `@luma_agent.instructions` decorator reading `OrchestratorDeps.system_prompt`, so a custom agent's prompt overrides the default at runtime.

### Specialists + teams (newer, see `docs/specs/2026-04-19-parallel-agents-design.md`)

- `agents/specialist/registry.py` — `SPECIALIST_REGISTRY: dict[str, Agent[...]]` mapping capability strings (e.g. `"text_to_image"`, `"vision"`, `"music_generation"`) to specialized PydanticAI agents. Includes back-compat aliases (`"image"` → `text_to_image_agent`, `"video"` → `text_to_video_agent`) for agents saved before the capability rename.
- `agents/team_planner.py` — produces a validated `TeamPlan` (DAG of `PlanNode`s, each bound to a specialist capability) from a user request.
- `agents/team_dag_executor.py` — runs the plan as an asyncio DAG with a global `DAG_MAX_PARALLEL = 5` cap, pushing per-node events onto a queue drained by `orchestrator.stream()`. Respects dependencies; emits CREDITS events alongside the usual TEXT/URL/STATUS/ERROR.
- `services/team.py` / `routers/teams.py` — Team CRUD; `Team.members` and `Team.orchestrator` are JSON columns, not relations.

Team runs share the same SSE contract as single-agent chat — the client doesn't need to know whether the response came from one agent or a DAG.

### Data model (`backend/prisma/schema.prisma`)

Cascades:

```
User ──► Board ──► Generation ──► GenerationVariant   (all Cascade)
  │        │           │
  │        └─► Agent ──┘    (Agent → Generation.agentId is SetNull on Agent delete)
  │        └─► Team
  └─► Agent, Team
```

Points that bite:
- `Agent.isActive` — `services.agent.delete_agent` is a **soft delete** (flips `isActive=false`); the row stays. No hard-delete endpoint exists.
- `Generation.status` is the `GenerationStatus` enum stored **uppercase** (`PENDING`/`PROCESSING`/`COMPLETED`/`FAILED`). The HTTP API and SSE `status` event lowercase it at the boundary.
- `Generation.resultUrl` is `null` for text-only generations — the text lives in `metadata.text`.
- `resultType` is inferred from the command: `/image` → `"image"`, `/video` → `"video"`, otherwise `"text"`.
- **Self-hosted credits:** `services/credits.py` returns early if `SELF_HOSTED=true` — unlimited credits. No Stripe integration.

### Auth

**Self-Hosted Mode:**
- Local username/password auth (`POST /auth/register`, `POST /auth/login`) — enabled by default when `SELF_HOSTED=true`
- GitHub OAuth optional — requires `GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET` and `ENABLE_GITHUB_AUTH=true`
- JWT in `localStorage`, HMAC-signed with `JWT_SECRET`, payload `{ sub: user_id, exp, iat }`, 24h default TTL
- Backend validates with `auth.dependencies.get_current_user` (`decode_token` → `services.user.get_user_by_id`)
- Logout is client-side; `POST /auth/logout` is a stub

Frontend sends `Authorization: Bearer *** on every request via `lib/api.ts`'s `request()` helper.

### Analytics (`media_agents/analytics/`)

PostHog integration. **Do not `import posthog` outside this package** — always go through `analytics.capture(...)` / `analytics.identify(...)`. Event names live as `Final[str]` constants in `analytics/events.py`; raw event-name strings anywhere else are a smell. Contract is tracked in `.telemetry/tracking-plan.yaml` — bump `meta.version` when adding events. When `POSTHOG_API_KEY` is unset the client is a no-op (safe for dev/CI). The `email` argument to `capture()` is only used for the internal-user guard — it is never forwarded to PostHog. See `backend/src/media_agents/analytics/README.md`.

Daily reconciliation: `uv run python -m scripts.sync_analytics_traits`.

### Frontend state (`src/stores/index.ts`)

All Zustand. Only `useAuthStore.token` is persisted (`persist` + `partialize`); everything else is in-memory and re-fetched on mount. `useAuthStore.checkAuth()` rehydrates `user` from `/auth/me` on every dashboard layout mount; failure redirects to `/login`.

Stores: `useAuthStore`, `useBoardStore`, `useChatStore`, `useHistoryStore`, `useAgentStore`, `useTeamStore`, `useBillingStore`.

**Self-hosted:** `useBillingStore.fetchStatus()` returns `ENTERPRISE` with 999999 credits locally when `NEXT_PUBLIC_SELF_HOSTED=true`. Billing nav link and upgrade modal hidden from dashboard layout.

### Streaming chat on the client

`components/chat/chat-panel.tsx` does **not** use `EventSource`. It POSTs to `/chat/stream` with fetch, reads `response.body` as a `ReadableStream`, and parses SSE line-by-line — tracking the current `event:` name across blank-line-delimited blocks and routing `data:` payloads. `generation_start` stores the generation id via `setGenerating(true, data)`.

### Routing (Next.js App Router)

Every page is `"use client"`; only layouts are server components (and they do nothing data-related). The app effectively runs as an SPA. Route groups `(auth)` and `(dashboard)` share `src/app/layout.tsx`. The `(dashboard)/layout.tsx` is the auth gate — it runs `checkAuth()` on mount and pushes to `/login` if the token is missing.

### Environment loading

`media_agents/main.py` calls `load_dotenv(Path(__file__).parent.parent.parent / ".env")` at import — so `.env` must live at `backend/.env`. `env.py` exports cached getters; read env vars through it rather than `os.environ` directly for anything user-configurable.

Docker Compose (`docker-compose.yml` at repo root) runs three services sharing networks: `postgres` (local DB), `backend` (waits for postgres healthy, runs migrations), `frontend` (waits for backend healthy). `schema.prisma` maps `directUrl = env("DIRECT_URL")` for migrations.

## Self-Hosted Configuration

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SELF_HOSTED` | `false` | Set `true` for self-hosted — unlimited credits, no Stripe |
| `PRISM_LICENSE_KEY` | `""` | Enterprise license for API endpoints (placeholder) |
| `ENABLE_LOCAL_AUTH` | `true if SELF_HOSTED` | Local username/password auth |
| `ENABLE_GITHUB_AUTH` | `true if GITHUB_CLIENT_ID` | GitHub OAuth |
| `NEXT_PUBLIC_SELF_HOSTED` | `false` | Frontend: hides billing UI, shows self-hosted messaging |

## Conventions

- **Backend tests** use `pytest-asyncio` with `asyncio_mode = "auto"` — async test functions don't need `@pytest.mark.asyncio`.
- **Prisma client must be generated** before the backend will import (`uv run prisma generate`). If you see `PrismaError: did not initialize`, run this first.
- **snake_case HTTP / camelCase DB** — stay consistent with the existing routers; don't refactor to unify them.
- **No backwards-compatibility shims** in new code unless the specialist registry alias pattern applies (renamed capabilities need to keep reading old saved agents).
- **Commits** — Conventional-ish ("Feat:", "Fix:", "Remove…") based on recent history. PRs welcome for non-trivial changes; `docs/plans/` and `docs/specs/` hold the larger designs.