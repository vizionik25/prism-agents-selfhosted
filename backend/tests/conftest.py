"""Shared fixtures.

Tests run without touching the database or fal.ai. The `auto_jwt_secret` fixture
guarantees a valid JWT_SECRET is set so the strict guard in
`media_agents.auth.jwt._get_jwt_secret` doesn't refuse to mint tokens during tests.
"""

from __future__ import annotations


import pytest


@pytest.fixture(autouse=True)
def auto_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a valid JWT_SECRET is in the env for every test."""
    monkeypatch.setenv("JWT_SECRET", "test-secret-" + "x" * 32)


@pytest.fixture
def unset_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Opt-in fixture for tests that need to verify the missing-secret guard."""
    monkeypatch.delenv("JWT_SECRET", raising=False)
