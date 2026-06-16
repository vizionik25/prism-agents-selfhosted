"""Tests for the /api-keys router — request/response models and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from media_agents.routers.api_keys import (
    CreateApiKeyRequest,
    ApiKeyResponse,
    ApiKeyListResponse,
    ApiKeyCreatedResponse,
)


def test_create_request_requires_name():
    with pytest.raises(ValidationError):
        CreateApiKeyRequest(agreed_to_disclaimer=True)


def test_create_request_accepts_valid_input():
    req = CreateApiKeyRequest(name="Production", agreed_to_disclaimer=True)
    assert req.name == "Production"
    assert req.agreed_to_disclaimer is True


def test_create_request_disclaimer_defaults_false():
    req = CreateApiKeyRequest(name="Test")
    assert req.agreed_to_disclaimer is False


def test_api_key_response_fields():
    resp = ApiKeyResponse(
        id="uuid-1",
        name="My Key",
        key_prefix="sk-prism-abc...",
        created_at="2026-06-14T00:00:00Z",
        last_used_at=None,
        revoked_at=None,
    )
    assert resp.id == "uuid-1"
    assert resp.revoked_at is None


def test_api_key_created_response_includes_raw_key():
    resp = ApiKeyCreatedResponse(
        id="uuid-1",
        name="My Key",
        key="sk-prism-fullrawkey123",
        key_prefix="sk-prism-ful...",
        created_at="2026-06-14T00:00:00Z",
    )
    assert resp.key.startswith("sk-prism-")


def test_api_key_list_response():
    resp = ApiKeyListResponse(keys=[])
    assert resp.keys == []
