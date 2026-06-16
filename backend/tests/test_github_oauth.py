"""Tests for the OAuth helpers that don't need network access.

The HTTP-bound helpers (exchange_code_for_token, get_github_user, etc.) are
intentionally not unit-tested here — they're thin httpx wrappers and would only
be exercised meaningfully via integration tests against a recorded fixture.
"""

from __future__ import annotations

import base64
import re
from urllib.parse import parse_qs, urlparse

import pytest

from media_agents.auth import github as oauth


def test_generate_state_is_urlsafe_base64() -> None:
    state = oauth.generate_state()
    assert len(state) > 32
    # Decoding should succeed on urlsafe base64
    base64.urlsafe_b64decode(state + "=" * (-len(state) % 4))
    # Only urlsafe-base64 chars
    assert re.fullmatch(r"[A-Za-z0-9_\-=]+", state)


def test_generate_state_is_unique() -> None:
    states = {oauth.generate_state() for _ in range(50)}
    assert len(states) == 50


def test_get_github_auth_url_contains_required_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("FRONTEND_URL", "https://app.example.com")

    # FRONTEND_URL is captured at import time in env.py; reload to pick it up.
    import importlib

    from media_agents import env as env_module

    importlib.reload(env_module)
    importlib.reload(oauth)

    state = "deterministic-state"
    url = oauth.get_github_auth_url(state)

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    assert parsed.netloc == "github.com"
    assert parsed.path == "/login/oauth/authorize"
    assert qs["client_id"] == ["test-client-id"]
    assert qs["state"] == [state]
    # scope must include the two we request
    assert qs["scope"] == ["read:user user:email"]
    assert qs["redirect_uri"] == ["https://app.example.com/auth/callback"]
