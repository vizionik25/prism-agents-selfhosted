import os
from functools import lru_cache


@lru_cache
def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


_FRONTEND_URL_RAW = get_env("FRONTEND_URL", "http://localhost:3000")
FRONTEND_URLS: list[str] = [
    u.strip() for u in _FRONTEND_URL_RAW.split(",") if u.strip()
]
FRONTEND_URL = FRONTEND_URLS[0]


DEMO_MODE: bool = get_env("DEMO_MODE", "false").lower() == "true"
SELF_HOSTED: bool = get_env("SELF_HOSTED", "false").lower() == "true"
PRISM_LICENSE_KEY: str = get_env("PRISM_LICENSE_KEY", "")
ENABLE_LOCAL_AUTH: bool = (
    get_env("ENABLE_LOCAL_AUTH", "true" if SELF_HOSTED else "false").lower() == "true"
)
ENABLE_GITHUB_AUTH: bool = (
    get_env(
        "ENABLE_GITHUB_AUTH", "true" if get_env("GITHUB_CLIENT_ID") else "false"
    ).lower()
    == "true"
)


def get_github_redirect_url() -> str:
    return f"{FRONTEND_URL}/auth/callback"
