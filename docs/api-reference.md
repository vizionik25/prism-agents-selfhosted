# API Reference

Complete reference for PrismAgents' HTTP API and all backend + frontend modules.

- [HTTP API](#http-api)
- [Backend modules](#backend-modules)
- [Frontend modules](#frontend-modules)

---

## HTTP API

All routes are mounted on the FastAPI app in `media_agents/main.py`. Authenticated routes require `Authorization: Bearer <jwt>`.

CORS is scoped to `FRONTEND_URL` (env var, default `http://localhost:3000`). Set it to your deployed frontend origin in production.

### Health

#### `GET /health`

Unauthenticated health probe.

**Response 200:** `{"status": "ok"}`

### Auth

Router: `media_agents.auth.router`.

#### `GET /auth/github`

Start the GitHub OAuth flow.

**Response 200:**
| Field | Type | Description |
|---|---|---|
| `url` | `string` | Pre-built GitHub authorization URL |
| `state` | `string` | Random 32-byte base64 state (client should round-trip it) |

#### `GET /auth/callback`

Complete the OAuth flow. GitHub redirects the browser here with `code` and `state` query params.

**Query parameters:**
| Field | Type | Required | Description |
|---|---|---|---|
| `code` | `string` | yes | OAuth authorization code from GitHub |
| `state` | `string` | yes | Round-tripped state value |

**Response 200:**
| Field | Type | Description |
|---|---|---|
| `access_token` | `string` | JWT |
| `token_type` | `string` | `"bearer"` |
| `user` | `object` | `{id, username, email, avatar_url}` |

**Errors:** `400` if token exchange, user fetch, or email lookup fails.

#### `POST /auth/logout`

Auth required. Currently a no-op on the server; token invalidation is client-side.

**Response 200:** `{"message": "Logged out successfully"}`

#### `GET /auth/me`

Auth required. Returns the current user.

**Response 200 (`UserResponse`):**
| Field | Type | Description |
|---|---|---|
| `id` | `string` (UUID) | Primary key |
| `username` | `string` | GitHub login |
| `email` | `string` | Primary email from GitHub |
| `avatar_url` | `string \| null` | GitHub avatar URL, if set |

### Boards

Router: `media_agents.routers.boards`. All routes require auth.

#### `GET /boards`

List the caller's boards, ordered by `updated_at` desc.

**Response 200:** `{ "boards": [BoardResponse, ...] }`

#### `POST /boards`

Create a board.

**Request body (`BoardCreate`):**
| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | yes | Display name |
| `description` | `string` | no | Free-text description |

**Response 201 (`BoardResponse`):** `{id, name, description, created_at, updated_at}`

#### `GET /boards/{board_id}`

Fetch a board the caller owns. Includes related agents via Prisma `include`.

**Response 200 (`BoardResponse`)** | **404** if not found or not owned.

#### `PUT /boards/{board_id}`

Update name and/or description.

**Request body (`BoardUpdate`):** both fields optional.

**Response 200 (`BoardResponse`)** | **404** if not found.

#### `DELETE /boards/{board_id}`

Hard delete (cascades to agents' `boardId` set-null and deletes all generations).

**Response 204** | **404** if not found.

### Agents

Router: `media_agents.routers.agents`. All routes require auth.

#### `GET /agents?board_id={uuid}`

List active agents for the caller. If `board_id` is provided, filter to that board.

**Response 200:** `{ "agents": [AgentResponse, ...] }`

#### `POST /agents`

Create an agent.

**Request body (`AgentCreate`):**
| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | yes | Display name |
| `system_prompt` | `string` | yes | Sent as the `system` message to the LLM |
| `description` | `string` | no | Free-text description |
| `board_id` | `UUID` | no | Attach to a board |
| `config` | `object` | no | Arbitrary JSON |

**Response 201 (`AgentResponse`):** `{id, name, description, system_prompt, board_id, config, created_at, updated_at}`

#### `GET /agents/{agent_id}`

**Response 200 (`AgentResponse`)** | **404** if not found or not owned.

#### `PUT /agents/{agent_id}`

**Request body (`AgentUpdate`):** `name`, `description`, `system_prompt`, `config` — all optional.

**Response 200 (`AgentResponse`)** | **404** if not found.

#### `DELETE /agents/{agent_id}`

**Soft delete** — sets `isActive=false`.

**Response 204** | **404** if not found.

### Generations

Router: `media_agents.routers.generations`. All routes require auth.

#### `GET /generations?board_id={uuid}`

List generations for a board, newest first. Includes ordered variants.

**Response 200:** `{ "generations": [GenerationResponse, ...] }`

#### `GET /generations/{generation_id}`

**Response 200 (`GenerationResponse`):**
| Field | Type | Description |
|---|---|---|
| `id` | `string` | Primary key |
| `board_id` | `string` | Parent board |
| `agent_id` | `string \| null` | Custom agent used, if any |
| `prompt` | `string` | The user's original chat message |
| `status` | `string` | `pending` \| `processing` \| `completed` \| `failed` (lowercased at the API boundary; DB stores the Prisma enum in uppercase) |
| `result_url` | `string \| null` | First asset URL (image/video). `null` for text-only results. |
| `result_type` | `string \| null` | `"image"`, `"video"`, or `"text"` |
| `metadata` | `object` | For text results: `{text, response_length}`. For asset results: arbitrary. |
| `variants` | `VariantResponse[]` | Ordered by `variant_index` |
| `created_at` | `string` | ISO 8601 |

`VariantResponse`: `{id, variant_index, result_url, result_type, metadata, created_at}`.

#### `DELETE /generations/{generation_id}`

**Response 204** | **404** if not found.

### Chat

Router: `media_agents.routers.chat`. Auth required.

#### `POST /chat/stream`

Open an SSE stream of the assistant's response. Implemented with `sse_starlette.EventSourceResponse`.

**Request body (`ChatRequest`):**
| Field | Type | Required | Description |
|---|---|---|---|
| `board_id` | `UUID` | yes | Target board |
| `message` | `string` | yes | User message (may start with a slash command) |
| `agent_id` | `UUID` | no | Custom agent whose system prompt should be used |
| `history` | `ChatMessage[]` | no | Prior turns: `{role: "user"\|"assistant", content: string}` |

**Response:** `text/event-stream`. Event sequence:

| Event | Data | When |
|---|---|---|
| `generation_start` | `<generation_id>` | Always, first event |
| `message` | assistant text chunk | For each `TEXT:` from the orchestrator |
| `url` | asset URL | When a generated image/video URL arrives |
| `status` | `processing` \| `completed` \| `failed` | On each orchestrator `STATUS:` |
| `error` | error message | If board not found, agent not found, or orchestrator yields `ERROR:` |
| `generation_end` | `""` | Always, last event |

On success the backend sets `status=COMPLETED`, stores the first asset URL in `Generation.resultUrl` (or `null` for text generations), fills `metadata = {text, response_length}`, and creates `GenerationVariant` rows for any additional URLs. On error it sets `status=FAILED`.

### API Keys

Router: `media_agents.routers.api_keys`. All routes require JWT auth (API keys cannot manage other API keys).

API key access is gated behind the Plus subscription tier or higher. Before creating the first key, users must agree to the API access disclaimer acknowledging that automated systems can consume credits faster than manual usage.

#### Authentication via API Key

All public endpoints (Chat, Agents, Teams, Boards, Generations) accept API key authentication alongside JWT. Use the key in the `Authorization` header:

```
Authorization: Bearer sk-prism-<your-key>
```

API key-authenticated requests deduct credits from the same pool as web UI usage. Billing and Auth endpoints remain JWT-only (internal, non-public-facing).

#### `POST /api-keys`

Create a new API key. Returns the full key **once** — it cannot be retrieved again.

**Request body (`CreateApiKeyRequest`):**
| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | yes | User-assigned label (1-64 chars) |
| `agreed_to_disclaimer` | `boolean` | no | Must be `true` on first key creation |

**Response 201 (`ApiKeyCreatedResponse`):**
| Field | Type | Description |
|---|---|---|
| `id` | `string` | Key UUID |
| `name` | `string` | Label |
| `key` | `string` | Full API key (**shown only once**) |
| `key_prefix` | `string` | Display prefix |
| `created_at` | `string` | ISO 8601 |

**Errors:** `403` if tier < Plus. `400` if disclaimer not agreed, 10 keys limit reached, or invalid name.

#### `GET /api-keys`

List all API keys for the current user.

**Response 200 (`ApiKeyListResponse`):** `{ "keys": [ApiKeyResponse, ...] }`

`ApiKeyResponse`: `{id, name, key_prefix, created_at, last_used_at, revoked_at}`

#### `DELETE /api-keys/{key_id}`

Revoke an API key (soft delete — sets `revoked_at`).

**Response 204** | **404** if not found or not owned.

---

## Backend modules

### `media_agents.main`

FastAPI app wiring.

- `lifespan(app)` — async context manager that calls `prisma.connect()` on startup and `prisma.disconnect()` on shutdown.
- `app` — `FastAPI(title="PrismAgents API", version="0.1.0", lifespan=lifespan)` with CORS scoped to `FRONTEND_URL` and all five routers mounted.
- `health()` — `GET /health` returning `{"status": "ok"}`.

Loads `.env` at import time via `load_dotenv(Path(__file__).parent.parent.parent / ".env")`.

### `media_agents.prisma`

Creates the single shared Prisma client: `prisma = Prisma()`. Imported everywhere DB access is needed. Connected/disconnected by `main.lifespan`.

### `media_agents.env`

Thin wrapper around `os.environ`.

| Function / Constant | Signature | Description |
|---|---|---|
| `get_env` | `(key: str, default: str = "") -> str` | `lru_cache`'d env lookup |
| `FRONTEND_URL` | `str` | Cached at import: `get_env("FRONTEND_URL", "http://localhost:3000")` |
| `get_github_redirect_url` | `() -> str` | `f"{FRONTEND_URL}/auth/callback"` |

### `media_agents.auth.jwt`

HS256 JWT encoding/decoding. Reads `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRATION_HOURS` from the environment lazily (on every call). `_get_jwt_secret` raises `RuntimeError` if `JWT_SECRET` is unset or shorter than 32 characters — there is no insecure default.

| Function | Signature | Description |
|---|---|---|
| `create_access_token` | `(user_id: uuid.UUID) -> str` | 24h TTL by default, payload `{sub, exp, iat}` (timezone-aware UTC) |
| `decode_token` | `(token: str) -> Optional[uuid.UUID]` | Returns `None` on any `JWTError` or missing `sub` |
| `_get_jwt_secret`, `_get_jwt_algorithm`, `_get_jwt_expiration_hours` | — | Private env readers |

### `media_agents.auth.github`

GitHub OAuth flow implementation using `httpx`.

| Function | Signature | Description |
|---|---|---|
| `generate_state` | `() -> str` | 32-byte urlsafe base64 random token |
| `get_github_auth_url` | `(state: str) -> str` | Builds the authorize URL with `read:user user:email` scopes |
| `exchange_code_for_token` | `(code: str) -> Optional[str]` | POSTs to `GITHUB_TOKEN_URL`, returns the `access_token` or `None` |
| `get_github_user` | `(access_token: str) -> Optional[dict]` | `GET /user` on GitHub API |
| `get_github_emails` | `(access_token: str) -> list` | `GET /user/emails`, filters to primary+verified |
| `get_primary_email` | `(access_token: str) -> Optional[str]` | Falls back from `/user` email to `/user/emails` |

Constants: `GITHUB_API_URL`, `GITHUB_AUTH_URL`, `GITHUB_TOKEN_URL`.

### `media_agents.auth.dependencies`

FastAPI auth dependencies using `HTTPBearer`.

| Function | Signature | Description |
|---|---|---|
| `get_current_user` | `(credentials = Depends(HTTPBearer())) -> dict` | Decodes JWT, loads user, raises `401` on failure |
| `get_optional_user` | `(credentials = Depends(HTTPBearer(auto_error=False))) -> Optional[dict]` | Non-failing variant for optionally-authenticated endpoints |

Module-level `security = HTTPBearer()`.

### `media_agents.auth.router`

Mounts `/auth/*`. See [HTTP API → Auth](#auth).

- `github_login()` — handler for `GET /auth/github`
- `github_callback(code, state)` — handler for `GET /auth/callback`; upserts the user and mints a JWT
- `logout(current_user)` — handler for `POST /auth/logout`
- `get_me(current_user)` — handler for `GET /auth/me`

Response models: `TokenResponse`, `UserResponse`.

### `media_agents.services.user`

| Function | Signature | Description |
|---|---|---|
| `get_user_by_id` | `(user_id: uuid.UUID) -> Optional[dict]` | Primary-key lookup |
| `get_user_by_github_id` | `(github_id: str) -> Optional[dict]` | Used by OAuth upsert |
| `create_user` | `(github_id, username, email, avatar_url=None, access_token=None) -> dict` | Insert a new user row |
| `update_user` | `(user_id, username=None, avatar_url=None, access_token=None) -> dict` | Patch selected fields |

### `media_agents.services.board`

| Function | Signature | Description |
|---|---|---|
| `get_boards_by_user` | `(user_id) -> list[dict]` | Ordered by `updatedAt desc` |
| `get_board_by_id` | `(board_id, user_id) -> Optional[dict]` | Ownership check; includes related `agents` |
| `create_board` | `(user_id, name, description=None) -> dict` | Insert a new board |
| `update_board` | `(board_id, user_id, name=None, description=None) -> Optional[dict]` | Ownership check via `get_board_by_id` |
| `delete_board` | `(board_id) -> None` | Hard delete (cascades) |

### `media_agents.services.agent`

| Function | Signature | Description |
|---|---|---|
| `get_agents_by_user` | `(user_id) -> list[dict]` | Filters to `isActive=True` |
| `get_agents_by_board` | `(board_id, user_id) -> list[dict]` | Filters to `isActive=True` |
| `get_agent_by_id` | `(agent_id, user_id) -> Optional[dict]` | Ownership check |
| `create_agent` | `(user_id, name, system_prompt, board_id=None, description=None, config=None) -> dict` | `config` defaults to `{}` |
| `update_agent` | `(agent_id, user_id, name=None, description=None, system_prompt=None, config=None) -> Optional[dict]` | Patch selected fields; `None` values are skipped |
| `delete_agent` | `(agent_id) -> None` | **Soft delete** — sets `isActive=False` |

### `media_agents.services.generation`

| Function | Signature | Description |
|---|---|---|
| `get_generations_by_board` | `(board_id, user_id) -> list[dict]` | Includes variants ordered by `variantIndex asc`; generations ordered by `createdAt desc` |
| `get_generation_by_id` | `(generation_id, user_id) -> Optional[dict]` | Ownership check; includes variants |
| `create_generation` | `(user_id, board_id, prompt, agent_id=None, status="PENDING") -> dict` | Insert a new generation in PENDING state |
| `update_generation` | `(generation_id, status=None, result_url=None, result_type=None, metadata=None) -> Optional[dict]` | Only sets provided fields |
| `add_variant` | `(generation_id, variant_index, result_url=None, result_type=None, metadata=None) -> dict` | Attach an additional asset variant |
| `delete_generation` | `(generation_id) -> None` | Hard delete (cascades variants) |

### `media_agents.routers.boards`

FastAPI router `/boards`. See [HTTP API → Boards](#boards).

- Request models: `BoardCreate`, `BoardUpdate`.
- Response models: `BoardResponse`, `BoardListResponse`.
- Helper: `_format_datetime(dt: datetime) -> str`.

### `media_agents.routers.agents`

FastAPI router `/agents`. See [HTTP API → Agents](#agents).

- Request models: `AgentCreate`, `AgentUpdate`.
- Response models: `AgentResponse`, `AgentListResponse`.

### `media_agents.routers.generations`

FastAPI router `/generations`. See [HTTP API → Generations](#generations).

- Response models: `VariantResponse`, `GenerationResponse`, `GenerationListResponse`.

### `media_agents.routers.chat`

FastAPI router `/chat` with a single endpoint `POST /chat/stream`.

| Symbol | Description |
|---|---|
| `ChatMessage` | `{role: str, content: str}` |
| `ChatRequest` | `{board_id: UUID, message: str, agent_id: UUID?, history: ChatMessage[]}` |
| `chat_event_generator(request, user_id)` | Async generator that creates a `Generation`, runs the orchestrator, and yields SSE events. See [architecture → Agent orchestration](architecture.md#agent-orchestration). |
| `chat_stream(request, current_user)` | Returns `EventSourceResponse(chat_event_generator(...))` |

### `media_agents.agents.client`

Asset generation via fal.ai. Single shared instance exported as `fal_client`. `fal_client` (the SDK package) reads `FAL_KEY` from env automatically.

**`FalClient`**
| Method | Signature | Returns |
|---|---|---|
| `generate_image` | `(prompt: str, model: str = "fal-ai/flux") -> str` | Image URL |
| `generate_video` | `(prompt: str, model: str = "fal-ai/kling-video/v1.6/commercial") -> str` | Video URL |
| `generate_speech` | `(text: str, voice: str = "alloy", model: str = "fal-ai/minimax/aura-phonetic") -> str` | Audio URL |

Chat completions live in `agents/fal_model.py`, not here.

### `media_agents.agents.fal_model`

Custom PydanticAI `Model` adapter wrapping `fal-ai/openrouter/chat/completions`.

| Symbol | Description |
|---|---|
| `fal_chat_model` | Module-level `FunctionModel` instance — passed to every PydanticAI `Agent` |
| `_fal_chat_function(messages, info) -> ModelResponse` | The translation layer: PydanticAI typed messages → OpenAI-style payload via `fal_client.run_async`, response → typed `ModelResponse` |

Non-streaming (fal.ai's chat completions don't deliver incremental chunks). Tool calls are passed through using OpenAI's tool-calling JSON schema.

### `media_agents.agents.templates`

**`AgentTemplate`** (Pydantic model): `{name, description, system_prompt, capabilities: list[str], default_config: dict}`

| Symbol | Description |
|---|---|
| `DEFAULT_TEMPLATES` | Five built-in templates: Image Generator, Video Creator, Brand Designer, Creative Writer, Research Analyst |
| `get_template(name)` | Case-insensitive lookup by name; returns `Optional[AgentTemplate]` |
| `get_all_templates()` | Returns the full list |

### `media_agents.agents.agent_maker`

PydanticAI `Agent` with `output_type=AgentTemplate` for structurally-validated agent generation.

| Symbol | Description |
|---|---|
| `_agent_maker` | `Agent[None, AgentTemplate]` using `fal_chat_model` and `retries=2` |
| `create_agent_from_description(user_description: str) -> AgentTemplate` | Runs the agent; on `UnexpectedModelBehavior` (validation exhausted) returns a fallback `AgentTemplate` with the user's description as `system_prompt` |

### `media_agents.agents.research`

| Symbol | Description |
|---|---|
| `_research_agent` | `Agent[None, str]` with research-specialist instructions, using `fal_chat_model` |
| `research_task(query: str, context: dict \| None = None) -> str` | Runs the research agent; returns the final text |

### `media_agents.agents.orchestrator`

Routes user messages through slash-command fast paths or a PydanticAI agent.

Module symbols:

| Symbol | Description |
|---|---|
| `SYSTEM_PROMPT` | Default Luma instructions used when no custom agent is active |
| `OrchestratorDeps` | Dataclass passed as PydanticAI `RunContext.deps`: `{user_id, board_id, system_prompt, asset_urls: list[str]}` |
| `luma_agent` | `Agent[OrchestratorDeps, str]` using `fal_chat_model`. Tools: `generate_image`, `generate_video`, `research`. Instructions resolved dynamically from `deps.system_prompt`. |

**`AgentOrchestrator`**
| Member | Signature | Description |
|---|---|---|
| `__init__` | `(user_id: uuid.UUID, board_id: uuid.UUID)` | Stores ids; `custom_agent` starts as `None` |
| `custom_agent` | `AgentTemplate \| None` | Active custom agent (set via `set_custom_agent` or `/create_agent`) |
| `set_custom_agent` | `(system_prompt: str, config: dict[str, Any])` | Wraps a raw system prompt into an `AgentTemplate` named "Custom Agent" |
| `_get_system_prompt` | `() -> str` | Returns the custom agent's system prompt if set, else module `SYSTEM_PROMPT` |
| `stream` | `(message: str, history: list[dict[str, str]]) -> AsyncGenerator[str, None]` | Main entry. Slash commands → `_handle_command` (fast path). Free-form → `luma_agent.run(...)`. Yields prefix-tagged strings (see [streaming protocol](architecture.md#agent-orchestration)). |
| `_parse_command` | `(message: str) -> dict[str, str] \| None` | Case-insensitive slash-command parser |
| `_handle_command` | `(command: dict[str, str]) -> AsyncGenerator[str, None]` | Slash-command dispatcher (image/video/research/create_agent/help) |

---

## Frontend modules

### `src/lib/api.ts`

Typed fetch client. Reads JWT from `localStorage.token` on every request.

| Symbol | Signature | Description |
|---|---|---|
| `request<T>` | `(endpoint, options?) -> Promise<T>` | Internal helper; sets `Authorization: Bearer`; throws with backend `detail` on non-OK |
| `api.auth.githubLogin` | `() => Promise<{url, state}>` | `GET /auth/github` |
| `api.auth.githubCallback` | `(code, state) => Promise<{access_token, user}>` | `GET /auth/callback?code=…&state=…` (URL-encoded) |
| `api.auth.me` | `() => Promise<User>` | `GET /auth/me` |
| `api.auth.logout` | `() => Promise<...>` | `POST /auth/logout` |
| `api.boards.list` | `() => Promise<{boards: Board[]}>` | `GET /boards` |
| `api.boards.create` | `({name, description?}) => Promise<Board>` | `POST /boards` |
| `api.boards.get` | `(id) => Promise<Board>` | `GET /boards/{id}` |
| `api.boards.update` | `(id, {name?, description?}) => Promise<Board>` | `PUT /boards/{id}` |
| `api.boards.delete` | `(id) => Promise<void>` | `DELETE /boards/{id}` |
| `api.agents.list` | `(boardId?) => Promise<{agents: Agent[]}>` | `GET /agents` (optional `?board_id=`) |
| `api.agents.create` | `({name, system_prompt, description?, board_id?, config?}) => Promise<Agent>` | `POST /agents` |
| `api.agents.get` | `(id) => Promise<Agent>` | `GET /agents/{id}` |
| `api.agents.update` | `(id, Partial<Agent>) => Promise<Agent>` | `PUT /agents/{id}` |
| `api.agents.delete` | `(id) => Promise<void>` | `DELETE /agents/{id}` — soft-delete on the backend (`isActive=false`) |
| `api.generations.list` | `(boardId) => Promise<{generations: Generation[]}>` | `GET /generations?board_id=` |
| `api.generations.get` | `(id) => Promise<Generation>` | `GET /generations/{id}` |
| `api.generations.delete` | `(id) => Promise<void>` | `DELETE /generations/{id}` |

Exported types: `User`, `Board`, `Agent`, `Generation`, `Variant`, `ChatMessage`. These must stay in sync with the backend Pydantic response models in `routers/*.py` (snake_case casing).

### `src/lib/utils.ts`

| Function | Description |
|---|---|
| `cn(...inputs)` | Tailwind class merger (`clsx` + `tailwind-merge`) |

### `src/stores/index.ts`

Zustand stores. Only `useAuthStore.token` is persisted to `localStorage` (`auth-storage` key) via `partialize`.

**`useAuthStore`** — `{ user, token, isLoading, setAuth(token, user), logout(), checkAuth() }`
- `setAuth` also writes `token` to `localStorage`
- `checkAuth` reads `localStorage.token`, calls `api.auth.me()`, clears on failure

**`useBoardStore`** — `{ boards, currentBoard, setBoards, setCurrentBoard, addBoard, updateBoard(id, data), removeBoard(id) }`

**`useChatStore`** — `{ messages, isGenerating, currentGenerationId, addMessage, updateLastMessage(content), setGenerating(bool, id?), clearMessages() }`

**`useHistoryStore`** — `{ generations, selectedGeneration, setGenerations, addGeneration, updateGeneration(id, data), setSelectedGeneration }`

**`useAgentStore`** — `{ agents, currentAgent, setAgents, setCurrentAgent, addAgent, removeAgent(id) }`

### `src/app/layout.tsx`

Root layout. Loads Geist Sans + Mono, wraps `children` in `TooltipProvider`. Sets `<html lang="en">` and applies `h-full antialiased` to `body`.

Metadata: `title="Luma - Creative Agents"`, `description="AI creative agents that make you prolific"`.

### `src/app/(auth)/layout.tsx`

Pass-through layout (`<>{children}</>`). Exists so the `(auth)` route group has its own segment.

### `src/app/(auth)/login/page.tsx`

`LoginPage` — calls `api.auth.githubLogin()`, saves `oauth_state` to localStorage, redirects the browser to the GitHub URL.

### `src/app/(auth)/auth/callback/page.tsx`

`AuthCallback` — wraps `AuthCallbackContent` in `Suspense` (required because it reads `useSearchParams`).

`AuthCallbackContent`:
1. Reads `code` and `state` from the URL.
2. Calls `api.auth.githubCallback(code, state)`.
3. Stores the JWT + user via `useAuthStore.setAuth`.
4. Clears `oauth_state` and redirects to `/`.
5. Falls back to `/login` on any error.

### `src/app/(dashboard)/layout.tsx`

`DashboardLayout` — the auth gate.

- Runs `useAuthStore.checkAuth()` on mount.
- Redirects to `/login` when `!isLoading && !token`.
- Renders a sidebar with logo, "Boards" nav link, and a user menu (avatar + logout).

### `src/app/(dashboard)/page.tsx`

`DashboardPage` — boards grid.

- Loads boards via `api.boards.list` on mount.
- "New Board" dialog creates via `api.boards.create`.
- Each board card links to `/boards/[id]`; dropdown menu offers rename (not wired) and delete.

### `src/app/(dashboard)/boards/[id]/page.tsx`

`BoardPage` — loads the board and renders three tabs:

- **Chat** → `<ChatPanel boardId={id} />`
- **History** → `<HistoryPanel boardId={id} />`
- **Agents** → link to `/boards/[id]/agent-creator`

Redirects to `/` on load failure.

### `src/app/(dashboard)/boards/[id]/agent-creator/page.tsx`

`AgentCreatorPage` — create agents from frontend-side templates (separate from backend `DEFAULT_TEMPLATES`; five hardcoded templates with emoji icons) or from scratch.

Left column: template picker + form. Right column: list of existing agents for this board with delete buttons.

### `src/components/chat/chat-panel.tsx`

`ChatPanel({ boardId })` — streaming chat UI.

- POSTs to `${NEXT_PUBLIC_API_URL}/chat/stream` with fetch, not `EventSource`.
- Reads the response as a `ReadableStream`, parses SSE blocks line-by-line (tracks the active `event:` name across a blank-line-delimited block).
- Handled events: `message` (appended to assistant text), `url` (appended on its own line), `error` (rendered inline), `generation_start` (stores the generation id via `setGenerating`). `status` and `generation_end` are informational.
- Provides three quick-action buttons that pre-fill the input with `/image`, `/video`, `/research`.
- Clears on error with "Sorry, something went wrong."

### `src/components/chat/history-panel.tsx`

`HistoryPanel({ boardId })` — two-pane history browser.

- Left: card list of generations with status dot + type badge + prompt preview.
- Right: detail view for the selected generation. Renders `result_url` as `<img>`, `<video>`, or plain text based on `result_type`. Shows up to N variants in a 3-col grid. Offers Copy URL / Open / Delete.

### `src/components/ui/*`

Standard shadcn/ui primitives: `avatar`, `badge`, `button`, `card`, `dialog`, `dropdown-menu`, `input`, `scroll-area`, `separator`, `skeleton`, `tabs`, `textarea`, `tooltip`. Registry config at `frontend/components.json`. Not documented here — see [shadcn/ui docs](https://ui.shadcn.com/docs).
