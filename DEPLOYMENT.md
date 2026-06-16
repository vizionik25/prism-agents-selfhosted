# Self-Hosted Deployment Guide

This guide covers deploying PrismAgents Self-Hosted using Docker Compose (recommended) or manual processes.

## Recommended: Docker Compose (Full Stack)

### Prerequisites
- Docker 24+ and Docker Compose v2+
- Your fal.ai API key ([sign up](https://fal.ai/))

### Quick Start

```bash
# 1. Clone the repo
git clone <your-repo>
cd prism-agents-selfhosted

# 2. Configure backend environment
cp backend/.env.docker.example backend/.env
# Edit backend/.env and set FAL_KEY (required)
# Optional: GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, PRISM_LICENSE_KEY

# 3. Configure frontend environment
cp frontend/.env.docker.example frontend/.env.local

# 4. Start the stack
docker compose up --build

# 5. Access the app
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000 (Swagger UI at /docs)
# PostgreSQL: localhost:5432 (user: postgres, password: postgres, db: prism_agents)
```

### Services Started

| Service | Port | Description |
|---|---|---|
| postgres | 5432 | PostgreSQL 16 (persistent volume) |
| backend | 8000 | FastAPI + PydanticAI |
| frontend | 3000 | Next.js 16 |

### Configuration

**Required** — Set in `backend/.env`:
- `FAL_KEY` — Your fal.ai API key (required for all AI generation)

**Optional** — Set in `backend/.env`:
- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` — Enable GitHub OAuth
- `PRISM_LICENSE_KEY` — Enterprise license for API endpoints (coming soon)
- `SENTRY_DSN` — Error tracking (backend)
- `SENTRY_AUTH_TOKEN` — Source map upload for Sentry

**Optional** — Set in `frontend/.env.local`:
- `NEXT_PUBLIC_SENTRY_DSN` — Error tracking (frontend)
- `SENTRY_DSN` — Same as above
- `SENTRY_AUTH_TOKEN` — Source map upload

### Making Changes & Rebuilding

```bash
# Rebuild specific service
docker compose build backend
docker compose up -d backend

# Rebuild everything
docker compose up --build

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Stop everything
docker compose down

# Stop and remove volumes (DELETES DATABASE)
docker compose down -v
```

### Health Checks

All services have health checks:
```bash
curl http://localhost:8000/health  # backend
curl http://localhost:3000/health  # frontend
```

---

## Manual Deployment (Without Docker Compose)

### Backend (FastAPI)

```bash
cd backend
uv sync
cp .env.example .env
# Fill in: DATABASE_URL (PostgreSQL), JWT_SECRET, FAL_KEY, FRONTEND_URL
uv run prisma generate
uv run prisma migrate deploy  # production: use deploy, NOT dev
uv run uvicorn media_agents.main:app --host 0.0.0.0 --port 8000 --workers 2
```

**Environment variables for production:**
- `DATABASE_URL` — Pooled Postgres connection (e.g. Neon, Supabase, RDS)
- `DIRECT_URL` — Direct connection (no `-pooler`) for migrations
- `JWT_SECRET` — ≥48 random chars: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `FAL_KEY` — Your fal.ai API key
- `FRONTEND_URL` — Your frontend origin (e.g. `https://app.yourdomain.com`)
- `SELF_HOSTED=true`
- `SENTRY_DSN` (optional) — Production Sentry project DSN
- `SENTRY_ENVIRONMENT=production`
- `SENTRY_TRACES_SAMPLE_RATE=0.1`
- `SENTRY_PROFILE_SAMPLE_RATE=0.1`

### Frontend (Next.js)

```bash
cd frontend
npm install
# Build with environment variables
NEXT_PUBLIC_API_URL=https://api.yourdomain.com \
NEXT_PUBLIC_SELF_HOSTED=true \
npm run build
npm start  # serves on port 3000
```

**For reverse proxy (nginx, Caddy, Traefik):**
- Proxy `https://app.yourdomain.com` → `http://localhost:3000`
- Proxy `https://api.yourdomain.com` → `http://localhost:8000`
- Ensure WebSockets/SSE pass through for `/chat/stream`

---

## GitHub OAuth (Optional)

1. Create OAuth app at github.com → Settings → Developer settings → OAuth Apps
2. **Homepage URL**: `https://your-frontend-domain.com`
3. **Callback URL**: `https://your-frontend-domain.com/auth/callback`
   - Note: callback handles redirect through frontend to backend
4. Add `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` to `backend/.env`
5. Set `ENABLE_GITHUB_AUTH=true` in `backend/.env`

---

## Upgrading

```bash
git pull
docker compose build --no-cache
docker compose up -d
# Migrations run automatically on backend startup
```

---

## Security Checklist

See [Security](docs/security.md) for full threat model. At minimum:

- [ ] Strong `JWT_SECRET` (≥48 chars)
- [ ] Database not exposed publicly
- [ ] TLS via reverse proxy (Let's Encrypt)
- [ ] `FRONTEND_URL` set exactly to your frontend origin
- [ ] Sentry configured for error monitoring
- [ ] Database backups configured (pg_dump cron)

---

## Troubleshooting

**Backend won't start — "JWT_SECRET must be set"**
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Add to backend/.env
```

**Database connection errors**
- Check `DATABASE_URL` format: `postgresql://user:pass@host:5432/db?sslmode=disable` (local Docker)
- For external DB: use pooled URL for `DATABASE_URL`, direct URL for `DIRECT_URL`

**Frontend shows white screen / login loop**
- Check `NEXT_PUBLIC_API_URL` matches backend URL
- Verify CORS: `FRONTEND_URL` in backend `.env` matches frontend origin exactly

**AI generation fails**
- Verify `FAL_KEY` is valid and has credits
- Check backend logs for fal.ai errors