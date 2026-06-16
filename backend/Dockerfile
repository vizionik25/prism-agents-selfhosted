# syntax=docker/dockerfile:1.7
# ──────────────────────────────────────────────────────────────
# PrismAgents backend — FastAPI + PydanticAI + Prisma
# Follows the canonical "Non-editable Installs" multi-stage pattern from:
#   https://docs.astral.sh/uv/guides/integration/docker/#non-editable-installs
#
# Key non-obvious bits:
#   - HOME=/app in BOTH stages. prisma-client-py bakes $HOME/.cache/prisma-python
#     paths INTO the generated Python client at `prisma generate` time. If the
#     builder runs with HOME=/root and the runtime user is `app`, the baked
#     /root paths are unreadable at runtime (mode 700). Pinning HOME=/app makes
#     the cache path stable and owned by `app`.
#   - libatomic1 installed in both stages — the Node binary prisma-client-py
#     downloads links against it, and python:3.12-slim doesn't include it.
#   - /app/src copied to runtime because uv_build with a src-layout writes a
#     .pth-style install (even under --no-editable) pointing at /app/src.
#   - Migrations run in a separate one-shot service (see docker-compose.yml)
#     that reuses this image with an overridden CMD.
# ──────────────────────────────────────────────────────────────

# ── Builder ────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_PYTHON_DOWNLOADS=0 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    HOME=/app

WORKDIR /app

# Plain BuildKit cache mount — works locally (docker compose), in Render's
# Docker builder, and anywhere else with BuildKit enabled. The cache is
# per-host (and per-builder on hosted CI), which is what we want.
RUN --mount=type=cache,id=uv-cache,target=/app/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable

COPY . /app

RUN --mount=type=cache,id=uv-cache,target=/app/.cache/uv \
    uv sync --locked --no-editable

# With HOME=/app, prisma-client-py puts its Node env + Prisma CLI + query engine
# under /app/.cache/prisma-python, and bakes THAT path into the generated Python
# client. Matching HOME in the runtime stage keeps those paths valid.
RUN uv run prisma generate

# ── Runtime ────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --home-dir /app --no-create-home app

WORKDIR /app

# All four copies land under /app which is owned by `app`. .cache/ carries the
# pre-warmed Node + Prisma CLI + query engine; no first-start download.
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/.cache /app/.cache
COPY --from=builder --chown=app:app /app/prisma /app/prisma
COPY --from=builder --chown=app:app /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HOME=/app \
    PORT=8000

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request,sys; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT','8000')}/health\", timeout=3); sys.exit(0)" || exit 1

# Default command runs the API. Honors $PORT so it works on Render (which
# injects PORT, default 10000) and locally (where compose pins PORT=8000).
# On Render the startCommand in render.yaml overrides this CMD to chain
# `prisma migrate deploy` before uvicorn (free tier has no preDeployCommand).
# Locally, the `migrate` service in docker-compose.yml runs migrations as a
# separate one-shot container before the api service starts.
CMD ["sh", "-c", "uvicorn media_agents.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
