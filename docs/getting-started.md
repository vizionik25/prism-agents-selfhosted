# Getting Started — PrismAgents Self-Hosted

Setup guide for running PrismAgents Self-Hosted locally. See [architecture.md](architecture.md) for design context and [api-reference.md](api-reference.md) for the HTTP surface.

## Quick Start (Docker Compose)

```bash
git clone <your-repo>
cd prism-agents-selfhosted

# Configure backend
cp backend/.env.docker.example backend/.env
# Edit backend/.env - REQUIRED: set FAL_KEY

# Configure frontend
cp frontend/.env.docker.example frontend/.env.local

# Start
docker compose up --build
```

Open <http://localhost:3000>. Register a local account or use GitHub OAuth.

---

## Prerequisites

- **Docker 24+** and **Docker Compose v2+** (recommended)
- **OR** for manual dev setup:
  - **Node.js 18+** (Next.js 16 minimum)
  - **Python 3.12+** (declared in `backend/.python-version`)
  - **[uv](https://github.com/astral-sh/uv)** for Python dependency management
  - **PostgreSQL** database (local or Neon)
  - **GitHub OAuth app** (optional — set callback to `http://localhost:3000/auth/callback`)
  - **fal.ai API key** ([sign up](https://fal.ai/))

---

## Manual Development Setup

### Backend (run from `backend/`)

```bash
cd backend
uv sync
cp .env.example .env
# Fill in required variables:
#   DATABASE_URL, JWT_SECRET (≥32 chars), FAL_KEY
#   GITHUB_CLIENT_ID/SECRET (optional)
#   SELF_HOSTED=true
uv run prisma generate
uv run prisma migrate dev
uv run uvicorn media_agents.main:app --host "0.0.0.0" --port 8200 --reload
```

FastAPI serves on `http://localhost:8200`. Interactive docs at `/docs` (Swagger UI) and `/redoc`. Health check at `/health`.

**Required variables (see `backend/.env.example`):**

| Variable | Description |
|---|---|
| `DATABASE_URL` | Postgres connection string (e.g. `postgresql://user:***@host/db?sslmode=require`) |
| `JWT_SECRET` | Random string, ≥32 characters |
| `JWT_ALGORITHM` | Default `HS256` |
| `JWT_EXPIRATION_HOURS` | Default `24` |
| `FAL_KEY` | **Required** — fal.ai API key for AI generation |
| `FRONTEND_URL` | Default `http://localhost:3000` — used for CORS |
| `SELF_HOSTED` | Set to `true` for self-hosted mode (unlimited credits) |
| `PRISM_LICENSE_KEY` | Enterprise license for API endpoints (coming soon) |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | Optional — for GitHub OAuth |
| `ENABLE_LOCAL_AUTH` | Defaults to `true` when `SELF_HOSTED=true` |
| `ENABLE_GITHUB_AUTH` | Defaults to `true` if `GITHUB_CLIENT_ID` is set |

---

### Frontend (run from `frontend/` in another terminal)

```bash
cd frontend
npm install

# Create .env.local
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8200
NEXT_PUBLIC_SELF_HOSTED=true
EOF

npm run dev
```

Open <http://localhost:3000>. You'll see a **Register** tab alongside **Continue with GitHub**.

---

## Common Tasks

### Backend (run from `backend/`)

| Task | Command |
|---|---|
| Install dependencies (incl. dev) | `uv sync` |
| Regenerate Prisma client after schema edit | `uv run prisma generate` |
| Create a new migration | `uv run prisma migrate dev --name <slug>` |
| Apply pending migrations | `uv run prisma migrate deploy` |
| Open Prisma Studio | `uv run prisma studio` |
| Run the test suite | `uv run pytest` |
| Run a single test file | `uv run pytest tests/test_jwt.py -v` |
| Lint | `uv run ruff check .` |

### Frontend (run from `frontend/`)

| Task | Command |
|---|---|
| Install dependencies | `npm install` |
| Lint | `npm run lint` |
| Production build | `npm run build` |
| Start production server | `npm start` |

---

## Verifying the Setup

1. **Backend health check**: `curl http://localhost:8000/health` → `{"status":"ok"}`
2. **Frontend loads**: visit <http://localhost:3000> and see the login/register page
3. **Register a local account**: Click **Register**, fill in username/email/password
4. **Create a board** → open it → send `/help` in chat to see slash commands

---

## Self-Hosted Mode Behavior

When `SELF_HOSTED=true` (backend) and `NEXT_PUBLIC_SELF_HOSTED=true` (frontend):

- **No Stripe billing** — all endpoints return ENTERPRISE tier with unlimited credits
- **Local auth enabled** — username/password registration and login work
- **GitHub OAuth optional** — only if you provide credentials
- **API key access gated** — requires `PRISM_LICENSE_KEY` (placeholder, coming soon)
- **UI changes** — Billing page hidden, upgrade modal shows "Enterprise Self-Hosted" info

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `PrismaError: did not initialize` | Run `uv run prisma generate` |
| OAuth callback returns to `/login` | Match `FRONTEND_URL` (backend) and GitHub OAuth callback URL exactly |
| 401 on every request | Token expired (24h default) or `JWT_SECRET` changed — clear `localStorage` |
| SSE stream ends immediately | Check `FAL_KEY` is valid; backend logs show fal.ai errors |
| Backend won't start: "JWT_SECRET must be set" | Generate: `python -c 'import secrets; print(secrets.token_urlsafe(48))'` |
| Build fails with `prisma generate` OOM | Increase Docker memory or run `prisma generate` locally first |

---

## Environment Loading

- **Backend**: Loads `.env` at import time via `load_dotenv` in `media_agents/main.py`, resolved relative to `backend/` (two directories up from `main.py`).
- **Frontend**: Reads `NEXT_PUBLIC_*` variables at build time; runtime secrets stay on the backend.
- **Docker Compose**: Uses `env_file` for backend and runtime `environment` overrides for container networking.

---

## Production Deployment

See [DEPLOYMENT.md](../DEPLOYMENT.md) for Docker Compose production deployment and manual setup instructions.

At minimum for production:
- [ ] Strong `JWT_SECRET` (≥48 chars)
- [ ] Managed PostgreSQL (Neon, Supabase, RDS)
- [ ] Reverse proxy with TLS (Let's Encrypt)
- [ ] `FRONTEND_URL` set to production frontend origin
- [ ] Sentry configured for error monitoring
- [ ] Database backups verified