"""Tests for dual auth middleware — JWT and API key authentication."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from media_agents.auth.dependencies import get_current_user
from media_agents.services.api_key import API_KEY_PREFIX, ALLOWED_TIERS


@pytest.fixture
def mock_credentials():
    def _make(token: str):
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return _make


@pytest.fixture
def plus_user():
    return {
        "id": str(uuid.uuid4()),
        "username": "testuser",
        "email": "test@example.com",
        "subscriptionTier": "PLUS",
        "subscriptionCredits": 100,
        "packCredits": 0,
    }


@pytest.fixture
def free_user():
    return {
        "id": str(uuid.uuid4()),
        "username": "freeuser",
        "email": "free@example.com",
        "subscriptionTier": "FREE_TRIAL",
        "subscriptionCredits": 0,
        "packCredits": 5,
    }


async def test_jwt_auth_still_works(mock_credentials, plus_user):
    jwt_token = "eyJhbGciOiJIUzI1NiJ9.not-a-real-jwt"
    creds = mock_credentials(jwt_token)
    with patch("media_agents.auth.dependencies.decode_token", return_value=uuid.UUID(plus_user["id"])), \
         patch("media_agents.auth.dependencies.user_service.get_user_by_id", new_callable=AsyncMock, return_value=plus_user):
        result = await get_current_user(creds)
        assert result["id"] == plus_user["id"]


async def test_api_key_authenticates_plus_user(mock_credentials, plus_user):
    api_key = f"{API_KEY_PREFIX}testapikey123456789"
    creds = mock_credentials(api_key)
    with patch("media_agents.auth.dependencies.api_key_service.lookup_by_raw_key", new_callable=AsyncMock, return_value=plus_user):
        result = await get_current_user(creds)
        assert result["id"] == plus_user["id"]


async def test_api_key_rejects_free_tier(mock_credentials, free_user):
    api_key = f"{API_KEY_PREFIX}testapikey123456789"
    creds = mock_credentials(api_key)
    with patch("media_agents.auth.dependencies.api_key_service.lookup_by_raw_key", new_callable=AsyncMock, return_value=free_user):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds)
        assert exc_info.value.status_code == 403


async def test_api_key_invalid_key_returns_401(mock_credentials):
    api_key = f"{API_KEY_PREFIX}nonexistentkey"
    creds = mock_credentials(api_key)
    with patch("media_agents.auth.dependencies.api_key_service.lookup_by_raw_key", new_callable=AsyncMock, return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds)
        assert exc_info.value.status_code == 401


async def test_api_key_checks_all_allowed_tiers(mock_credentials):
    for tier in ALLOWED_TIERS:
        user = {
            "id": str(uuid.uuid4()),
            "username": f"user_{tier}",
            "email": f"{tier}@example.com",
            "subscriptionTier": tier,
            "subscriptionCredits": 100,
            "packCredits": 0,
        }
        api_key = f"{API_KEY_PREFIX}testkey{tier}"
        creds = mock_credentials(api_key)
        with patch("media_agents.auth.dependencies.api_key_service.lookup_by_raw_key", new_callable=AsyncMock, return_value=user):
            result = await get_current_user(creds)
            assert result["subscriptionTier"] == tier
