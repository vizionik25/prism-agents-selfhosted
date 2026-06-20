import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Initialize Sentry before importing FastAPI so that ASGI integrations can properly hook into the application at import time.
import sentry_sdk  # noqa: E402
from sentry_sdk.integrations.asyncio import AsyncioIntegration  # noqa: E402

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
    release=os.environ.get("SENTRY_RELEASE"),
    send_default_pii=True,
    traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
    profile_session_sample_rate=float(
        os.environ.get("SENTRY_PROFILE_SAMPLE_RATE", "1.0")
    ),
    profile_lifecycle="trace",
    enable_logs=True,
    # Preserve PydanticAI tool error chains through the ASGI middleware.
    _experiments={"suppress_asgi_chained_exceptions": False},
    integrations=[AsyncioIntegration()],
)

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from media_agents.env import DEMO_MODE, FRONTEND_URLS  # noqa: E402
from media_agents.prisma import prisma  # noqa: E402
from media_agents.analytics import analytics  # noqa: E402
from media_agents.auth.router import router as auth_router  # noqa: E402
from media_agents.routers.boards import router as boards_router  # noqa: E402
from media_agents.routers.agents import router as agents_router  # noqa: E402
from media_agents.routers.teams import router as teams_router  # noqa: E402
from media_agents.routers.generations import router as generations_router  # noqa: E402
from media_agents.routers.chat import router as chat_router  # noqa: E402
from media_agents.routers.billing import router as billing_router  # noqa: E402
from media_agents.routers.api_keys import router as api_keys_router  # noqa: E402
from media_agents.routers.admin import router as admin_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    await prisma.connect()
    try:
        yield
    finally:
        analytics.shutdown()
        await prisma.disconnect()


app = FastAPI(
    title="PrismAgents API",
    description="AI creative agents platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if DEMO_MODE else FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 🛡️ Sentinel: Add essential security headers to all responses to protect against XSS, clickjacking, and mime-sniffing
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    return response


app.include_router(auth_router)
app.include_router(boards_router)
app.include_router(agents_router)
app.include_router(teams_router)
app.include_router(generations_router)
app.include_router(chat_router)
app.include_router(billing_router)
app.include_router(api_keys_router)
app.include_router(admin_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
