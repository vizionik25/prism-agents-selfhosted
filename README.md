# PrismAgents Self-Hosted

A creative AI agents platform for self-hosting: organize projects into boards, chat with streaming AI agents, and generate images, video, and text through your own fal.ai API key.

- **Frontend** — Next.js 16 (App Router) + React 19 + Tailwind v4 + shadcn/ui + Zustand
- **Backend** — FastAPI + Prisma (Python client) + sse-starlette, managed with `uv`
- **AI** — PydanticAI agent (custom `FunctionModel` adapter) over OpenRouter chat completions and image/video/speech models, all proxied through fal.ai
- **Auth** — Local username/password + optional GitHub OAuth → JWT (stored in `localStorage`)
- **Database** — PostgreSQL (local via Docker Compose or external like Neon)

## Key Differences from Cloud Version

- **No Stripe billing** — All features unlocked with unlimited credits
- **Bring your own API keys** — Provide your own `FAL_KEY` for AI generation
- **Local-first auth** — Username/password registration (GitHub OAuth optional)
- **Self-hosted Enterprise license** — API endpoint access requires a license key (coming soon)
- **Docker Compose** — Single command to spin up the entire stack

## Quick Start (Docker Compose - Recommended)

```bash
# 1. Clone and configure
git clone <your-repo>
cd prism-agents-selfhosted

# 2. Configure backend
cp backend/.env.docker.example backend/.env
# Edit backend/.env - REQUIRED: set FAL_KEY
# Optional: GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, PRISM_LICENSE_KEY

# 3. Configure frontend
cp frontend/.env.docker.example frontend/.env.local

# 4. Start everything
docker compose up --build

# 5. Open http://localhost:3000
# Register a local account (username/password) and start creating!
```

## Quick Start (Local Development)

### Backend (run from `backend/`)

```bash
cd backend
uv sync
cp .env.example .env    # Fill in DATABASE_URL, GITHUB_CLIENT_ID/SECRET (optional), JWT_SECRET, FAL_KEY
uv run prisma generate
uv run prisma migrate dev
uv run uvicorn media_agents.main:app --host "0.0.0.0" --port 8200 --reload
```

### Frontend (run from `frontend/` in another terminal)

```bash
cd frontend
npm install
echo 'NEXT_PUBLIC_API_URL=http://localhost:8200' > .env.local
echo 'NEXT_PUBLIC_SELF_HOSTED=true' >> .env.local
npm run dev
```

Visit <http://localhost:3000>. In self-hosted mode, you'll see a **Register** tab alongside GitHub login.

## Features

- Local username/password authentication (GitHub OAuth optional)
- Create boards (projects) to organize work
- Streaming chat with a default agent or your custom agent
- Slash commands: `/image`, `/video`, `/research`, `/create_agent`, `/help`
- Custom agents from five built-in templates or your own system prompt
- Generation history with result previews and variants
- Unlimited credits in self-hosted mode
- Self-hosted Enterprise license gating for API endpoints (coming soon)

## Documentation

- [Getting Started](docs/getting-started.md) — installation, environment variables, first run
- [Architecture](docs/architecture.md) — layered design, streaming protocol, data model
- [API Reference](docs/api-reference.md) — every REST endpoint and every module
- [Security](docs/security.md) — controls in place, open issues, hardening checklist

## Repository Layout

```text
prism-agents-selfhosted/
├── backend/                  # FastAPI app
│   ├── prisma/schema.prisma  # data model (User, Board, Agent, Generation, GenerationVariant)
│   ├── Dockerfile            # Multi-stage Docker build
│   └── src/media_agents/
│       ├── main.py           # FastAPI entrypoint + lifespan + CORS
│       ├── auth/             # Local auth + GitHub OAuth + JWT
│       ├── routers/          # HTTP routes (boards, agents, generations, chat, billing*)
│       ├── services/         # DB access layer over Prisma
│       └── agents/           # orchestrator, fal.ai client, templates, research, agent-maker
├── frontend/                 # Next.js app
│   ├── Dockerfile            # Multi-stage Docker build (standalone output)
│   └── src/
│       ├── app/              # App Router (route groups: (auth), (dashboard))
│       ├── components/       # chat/, agent/, board/, auth/, ui/ (shadcn)
│       ├── lib/api.ts        # typed fetch client with Bearer auth
│       └── stores/index.ts   # Zustand stores (auth, boards, chat, history, agents)
├── docker-compose.yml        # Full stack: postgres + backend + frontend
└── docs/                     # Documentation
```

\* `billing` endpoints are stubbed in self-hosted mode — return ENTERPRISE tier with unlimited credits; Stripe endpoints return 501 Not Implemented.

## Self-Hosted Configuration

Set these in `backend/.env`:

| Variable | Required | Description |
|---|---|---|
| `SELF_HOSTED` | Yes | Set to `true` — enables unlimited credits, hides Stripe UI |
| `FAL_KEY` | Yes | Your fal.ai API key for AI generation |
| `PRISM_LICENSE_KEY` | No* | Enterprise license key for API access (placeholder, coming soon) |
| `ENABLE_LOCAL_AUTH` | No | Defaults to `true` when `SELF_HOSTED=true` |
| `ENABLE_GITHUB_AUTH` | No | Set if you have GitHub OAuth credentials |

Frontend (`frontend/.env.local`):

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_SELF_HOSTED` | Yes | Set to `true` — hides billing, shows self-hosted UI |

## License

Licensed under the **Elastic License 2.0 (ELv2)** — see [LICENSE](LICENSE) for details.

This license allows:
- ✅ Free self-hosted use (personal, internal, non-commercial)
- ✅ Free use as part of a larger product/service that adds substantial value
- ❌ Offering the software as a managed service / SaaS / cloud service to third parties

For commercial SaaS offerings, managed hosting, or enterprise features (API access, SSO, etc.), a commercial license is available — contact us for details.