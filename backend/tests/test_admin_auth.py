"""Tests for admin auth dependencies."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from media_agents.auth.dependencies import (
    require_admin,
    require_super_admin,
    get_current_user,
)
from media_agents.services.api_key import API_KEY_PREFIX


@pytest.fixture
def super_admin():
    return {
        "id": str(uuid.uuid4()),
        "username": "owner",
        "email": "owner@prismagents.com",
        "role": "SUPER_ADMIN",
        "subscriptionTier": "PRO",
        "subscriptionCredits": 250,
        "packCredits": 0,
    }


@pytest.fixture
def admin_user():
    return {
        "id": str(uuid.uuid4()),
        "username": "admin1",
        "email": "admin@prismagents.com",
        "role": "ADMIN",
        "subscriptionTier": "PRO",
        "subscriptionCredits": 250,
        "packCredits": 0,
    }


@pytest.fixture
def regular_user():
    return {
        "id": str(uuid.uuid4()),
        "username": "regular",
        "email": "user@example.com",
        "role": "USER",
        "subscriptionTier": "STARTER",
        "subscriptionCredits": 30,
        "packCredits": 0,
    }


async def test_require_admin_allows_super_admin(super_admin):
    result = await require_admin(super_admin)
    assert result["role"] == "SUPER_ADMIN"


async def test_require_admin_allows_admin(admin_user):
    result = await require_admin(admin_user)
    assert result["role"] == "ADMIN"


async def test_require_admin_rejects_regular_user(regular_user):
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(regular_user)
    assert exc_info.value.status_code == 403


async def test_require_admin_rejects_missing_role():
    user = {"id": str(uuid.uuid4()), "username": "norole", "email": "no@role.com"}
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(user)
    assert exc_info.value.status_code == 403


async def test_require_super_admin_allows_super_admin(super_admin):
    result = await require_super_admin(super_admin)
    assert result["role"] == "SUPER_ADMIN"


async def test_require_super_admin_rejects_admin(admin_user):
    with pytest.raises(HTTPException) as exc_info:
        await require_super_admin(admin_user)
    assert exc_info.value.status_code == 403


async def test_require_super_admin_rejects_regular_user(regular_user):
    with pytest.raises(HTTPException) as exc_info:
        await require_super_admin(regular_user)
    assert exc_info.value.status_code == 403
