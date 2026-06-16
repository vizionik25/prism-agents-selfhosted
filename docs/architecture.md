# Architecture — PrismAgents Self-Hosted

High-level design of the PrismAgents stack. For endpoint-by-endpoint and module-by-module specifics, see [api-reference.md](api-reference.md).

## Components

```text
┌────────────────────────┐      ┌──────────────────────────┐      ┌─────────────┐
│   Next.js 16           │◄────►│   FastAPI (uvicorn)      │◄────►│   Postgres  │
│   App Router (client)  │ JSON │   sse-starlette for SSE  │Prisma│   (Local)   │
│   Zustand + lib/api.ts │      │   services/ → prisma     │      └─────────────┘
└─────────┬──────────────┘      └─────────┬────────────────┘
          │ OAuth redirect                │ HTTP (OpenRouter, fal models)
          ▼                               ▼
   ┌─────────────┐                  ┌───────────┐
   │   GitHub    │                  │  fal.ai   │
   │   OAuth     │                  └───────────┘
   └─────────────┘                        │
          │ Optional                    Your FAL_KEY
          ▼
   Local Auth
   (username/password)
```

Every page is marked `"use client"` — only the root and route-group layouts are server components, and they do nothing data-related. The app effectively runs as an SPA against the FastAPI JSON/SSE API. Auth is a JWT in `localStorage`.

## Self-Hosted Specifics

- **No Stripe** — Billing endpoints stubbed to return `ENTERPRISE` tier with unlimited credits
- **Local auth** — `services/user.py` provides `create_local_user`, `get_user_by_email`, `verify_password`
- **License gating** — API key endpoints check `PRISM_LICENSE_KEY` via `LicenseService` (placeholder)
- **Docker Compose** — Full stack: postgres + backend + frontend with health checks

## Layered Backend

```text
HTTP request
    │
    ▼
routers/<resource>.py   ← FastAPI path ops, Pydantic request/response models,
    │                     auth dependency, snake_case ↔ camelCase marshalling
    ▼
services/<resource>.py  ← the only layer that imports `prisma`
    │                     returns Prisma row dicts (camelCase)
    ▼
prisma.Prisma (single shared instance in media_agents.prisma)
    │
    ▼
Postgres
```

**Rule:** routers do not import `prisma` directly — go through the matching `services/*.py` module.

**Casing convention:** Prisma Python client fields are camelCase (`systemPrompt`, `avatarUrl`, `createdAt`). HTTP responses use snake_case (`system_prompt`, `avatar_url`, `created_at`) per FastAPI/Pydantic convention. Each router has a private `_format_datetime` helper and explicit field mapping in its response model constructors.

## Agent Orchestration

The AI-facing code lives in `media_agents/agents/` and is independent of HTTP. The orchestrator is built on **PydanticAI** with a custom model adapter that proxies through fal.ai's OpenRouter wrapper (so we keep the existing `FAL_KEY` credential and don't need a separate OpenAI/OpenRouter key).

### Flow for a Chat Message

1. `routers/chat.py::chat_stream` receives `{board_id, message, agent_id?, history}`.
2. It creates a `Generation` row (status `PENDING`) and emits a `generation_start` SSE event with the generation id.
3. It instantiates `AgentOrchestrator(user_id, board_id)`. If `agent_id` is provided, the custom agent's system prompt is wired in via `set_custom_agent`.
4. `orchestrator.stream(message, history)` is an async generator with two paths:
   - **Slash-command fast path** — `/image`, `/video`, `/research`, `/create_agent`, `/help` skip the LLM entirely, calling tools directly. Deterministic, no token cost.
   - **Free-form path** — input is run through `luma_agent`, a PydanticAI `Agent` with three registered tools (`generate_image`, `generate_video`, `research`). The LLM decides whether to call them. The active system prompt comes from `OrchestratorDeps.system_prompt` via a dynamic `@luma_agent.instructions` decorator, so a custom agent's prompt overrides the default at runtime.
5. The orchestrator yields tagged string chunks. The router translates them into SSE events and updates the `Generation` row:

| Prefix | SSE event | DB side-effect |
|--------|-----------|----------------|
| `TEXT:` | `message` | accumulated into `metadata.text` at end |
| `URL:` | `url` | first URL → `Generation.result_url`; subsequent URLs → `GenerationVariant` rows |
| `STATUS:` | `status` (lowercase ``) | `update_generation(status=.upper())` to match the Prisma enum |
| `ERROR:` | `error` | `update_generation(status="FAILED")` and stream ends |

6. Final `generation_end` event closes the stream. If successful, the router calls `update_generation(status="COMPLETED", result_url=<first_url_or_none>, result_type=<inferred>, metadata={text, response_length})`. The result type is inferred from the command: `/image` → `"image"`, `/video` → `"video"`, otherwise `"text"`.

This prefix-tagged stream is the sole contract between `agents/orchestrator.py` and `routers/chat.py`. The orchestrator never touches HTTP; the router never touches fal.ai.

### Slash Commands

Parsed in `AgentOrchestrator._parse_command`:

| Command | Handler | Effect |
|---------|---------|--------|
| `/image <prompt>` | `fal_client.generate_image` | yields `TEXT:Generating...` then `URL:<url>` |
| `/video <prompt>` | `fal_client.generate_video` | yields `TEXT:Generating...` then `URL:<url>` |
| `/research <query>` | `agents.research.research_task` | yields research summary as `TEXT:` |
| `/create_agent <desc>` | `agents.agent_maker.create_agent_from_description` | LLM-generates an `AgentTemplate` and activates it |
| `/help` | inline | yields the help text as `TEXT:` |

Non-command input falls through to the PydanticAI agent with the full message history plus the active system prompt (default or custom agent's).

## Specialist Agents + Teams (Parallel)

- `agents/specialist/registry.py` — `SPECIALIST_REGISTRY` mapping capability strings to specialized PydanticAI agents
- `agents/team_planner.py` — produces a validated `TeamPlan` (DAG of `PlanNode`s) from a user request
- `agents/team_dag_executor.py` — runs the plan as an asyncio DAG with `DAG_MAX_PARALLEL = 5` cap
- `services/team.py` / `routers/teams.py` — Team CRUD; `Team.members` and `Team.orchestrator` are JSON columns

Team runs share the same SSE contract as single-agent chat — the client doesn't need to know whether the response came from one agent or a DAG.

## fal.ai Boundary

Two modules touch `fal_client` (the official Python SDK package):

- `agents/client.py::FalClient` — asset generation only (`generate_image`, `generate_video`, `generate_speech`). Module-level singleton `fal_client = FalClient()`.
- `agents/fal_model.py` — a PydanticAI `FunctionModel` that translates between PydanticAI's typed messages and `fal-ai/openrouter/chat/completions`'s OpenAI-style payload. Used by `luma_agent`, `_agent_maker`, and `_research_agent`.

`fal_client` reads `FAL_KEY` from the environment automatically. The chat adapter calls `fal_client.run_async(...)` and returns a single full `ModelResponse`, so `agent.run()` is the right call pattern. fal.ai itself supports streaming (`fal_client.stream_async`) — the non-streaming behavior is a property of this adapter. The user-visible SSE stream from `routers/chat.py` comes from the orchestrator chunking its output as `TEXT:`/`URL:`/`STATUS:` events, not from token-level LLM streaming.

## Data Model

Prisma schema at `backend/prisma/schema.prisma`. Cascade rules:

```text
User ──(cascade)──► Board ──(cascade)──► Generation ──(cascade)──► GenerationVariant
  │                   │                       │
  │                   └─(SetNull)──► Agent ───┘  (agentId is SetNull on Agent delete)
  └─(cascade)──► Agent
```

- `Agent` has `isActive: Boolean` — `services.agent.delete_agent` is a **soft delete** that flips the flag; it does not remove the row.
- `Generation.status` is the Prisma `GenerationStatus` enum, stored uppercase (`PENDING`/`PROCESSING`/`COMPLETED`/`FAILED`). The HTTP API and SSE `status` event lowercase it at the boundary.
- `Generation.resultUrl` holds the first generated asset URL (image/video). For text-only generations it is `null` and the text lives in `metadata.text`. `resultType` is one of `"image"`, `"video"`, `"text"`.
- `GenerationVariant` rows are created for additional URLs beyond the first.
- `User` has `stripeCustomerId` and `stripeSubscriptionId` columns (unused in self-hosted) and `passwordHash` for local auth.
- `SubscriptionTier` includes `ENTERPRISE` — self-hosted mode returns this with unlimited credits.

## Authentication

```
Browser                 Next.js                 FastAPI                GitHub
   │                       │                       │                      │
   │ visit /login          │                       │                      │
   ├──────────────────────►│                       │                      │
   │                       │ GET /auth/github      │                      │
   ├──────────────────────►│──────────────────────►│                      │
   │◄──────────────────────┤◄──────────────────────┤ { url, state }       │
   │ window.location = url │                       │                      │
   ├───────────────────────┴──────────────────────────────────────────────►│
   │                                                                      │
   │◄─────────────────────────────── redirect /auth/callback?code&state ──┤
   │                       │                       │                      │
   │ GET /auth/callback    │ GET /auth/callback    │                      │
   ├──────────────────────►│──────────────────────►│                      │
   │                       │                       │ exchange_code_for_... │
   │                       │                       ├─────────────────────►│
   │                       │                       │◄──access_token───────┤
   │                       │                       │ upsert User         │
   │                       │                       │ create_access_token  │
   │                       │◄──{access_token, user}│                      │
   │ localStorage.setItem  │                       │                      │
   ◄──────────────────────┤                       │                      │
```

**Local Auth (Self-Hosted):**
- `POST /auth/register` — creates user with hashed password
- `POST /auth/login` — verifies password, returns JWT

- JWT is HMAC-signed with `JWT_SECRET`, payload `{ sub: user_id, exp, iat }`, 24h default TTL.
- Frontend sends `Authorization: Bearer ***` on every request via `lib/api.ts`'s `request()` helper.
- Backend validates with `auth.dependencies.get_current_user` → `auth.jwt.decode_token` → `services.user.get_user_by_id`.
- Logout is client-side (clears `localStorage`); `POST /auth/logout` is a stub.

## Frontend State

All state lives in Zustand stores (`src/stores/index.ts`). Only `useAuthStore.token` is persisted (`persist` middleware with `partialize`); everything else is in-memory and re-fetched on mount.

| Store | State | Used by |
|-------|-------|---------|
| `useAuthStore` | `{ user, token, isLoading, setAuth, logout, checkAuth }` | root, dashboard layout, login page |
| `useBoardStore` | boards list + currentBoard | dashboard page, board page |
| `useChatStore` | messages, isGenerating, currentGenerationId | `ChatPanel` |
| `useHistoryStore` | generations list, selectedGeneration | `HistoryPanel` |
| `useAgentStore` | agents list, currentAgent | `AgentCreatorPage` |
| `useTeamStore` | teams list, currentTeam | team pages |
| `useBillingStore` | tier, credits, fetchStatus | dashboard layout, billing page |

`useAuthStore.checkAuth()` rehydrates `user` from `/auth/me` on every dashboard layout mount. If no token or `/auth/me` fails, it clears state and the layout redirects to `/login`.

In self-hosted mode (`NEXT_PUBLIC_SELF_HOSTED=true`):
- `useBillingStore.fetchStatus()` returns `ENTERPRISE` with 999999 credits locally
- Billing nav link and upgrade modal hidden from dashboard layout

## Routing

Next.js App Router. Route groups `(auth)` and `(dashboard)` share `src/app/layout.tsx`.

```text
/                                 → (dashboard)/page.tsx        boards list
/boards/[id]                      → (dashboard)/boards/[id]/page.tsx    board view (Chat/History/Agents tabs)
/boards/[id]/agent-creator        → (dashboard)/boards/[id]/agent-creator/page.tsx  agent creator
/login                            → (auth)/login/page.tsx       Local auth + GitHub OAuth entry
/auth/callback                    → (auth)/auth/callback/page.tsx   OAuth return handler
/enterprise-license               → (dashboard)/enterprise-license/page.tsx  License info (coming soon)
/settings/billing                 → (dashboard)/settings/billing/page.tsx   Shows plan, hidden in self-hosted
```

The dashboard layout (`(dashboard)/layout.tsx`) is the auth gate: it runs `checkAuth()` on mount and pushes to `/login` if the token is missing after load.

## Streaming Chat on the Client

`components/chat/chat-panel.tsx` does **not** use `EventSource`. It POSTs to `/chat/stream` with fetch, reads the response body as a `ReadableStream`, and parses SSE line-by-line — tracking the current `event:` name across blank-line-delimited event blocks and routing `data:` payloads accordingly. It handles:

- `message` → appended to the assistant message.
- `url` → appended on its own line (clickable URL text).
- `error` → rendered inline as `Error: <detail>`.
- `generation_start` → stores the generation id in `useChatStore.currentGenerationId` via `setGenerating(true, data)`.
- `status`, `generation_end` → informational, no UI change.

## Operational Notes

- CORS is scoped to `FRONTEND_URL` from env (default `http://localhost:3000`).
- `services.agent.delete_agent` is a soft delete; the row stays with `isActive=false`. Hard delete is not exposed.
- In self-hosted mode, billing endpoints are stubbed:
  - `GET /billing/status` → `ENTERPRISE`, 999999 credits
  - `POST /billing/checkout` → 501 Not Implemented
  - `POST /billing/webhook` → 501 Not Implemented
  - `GET /billing/portal` → 501 Not Implemented