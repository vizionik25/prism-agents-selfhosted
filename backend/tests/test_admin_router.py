"""Tests for the /admin router — request/response models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from media_agents.routers.admin import (
    ChangeTierRequest,
    GrantCreditsRequest,
    ChangeRoleRequest,
    AdminUserSummary,
    AdminUserListResponse,
)


def test_change_tier_requires_tier():
    with pytest.raises(ValidationError):
        ChangeTierRequest()


def test_change_tier_accepts_valid():
    req = ChangeTierRequest(tier="PLUS")
    assert req.tier == "PLUS"


def test_grant_credits_accepts_subscription_only():
    req = GrantCreditsRequest(subscription_credits=100)
    assert req.subscription_credits == 100
    assert req.pack_credits is None


def test_grant_credits_accepts_pack_only():
    req = GrantCreditsRequest(pack_credits=50)
    assert req.pack_credits == 50
    assert req.subscription_credits is None


def test_change_role_requires_role():
    with pytest.raises(ValidationError):
        ChangeRoleRequest()


def test_change_role_accepts_valid():
    req = ChangeRoleRequest(role="ADMIN")
    assert req.role == "ADMIN"


def test_user_summary_fields():
    summary = AdminUserSummary(
        id="uuid",
        username="test",
        email="test@test.com",
        role="USER",
        subscription_tier="FREE_TRIAL",
        subscription_credits=0,
        pack_credits=5,
        created_at="2026-06-14T00:00:00Z",
    )
    assert summary.role == "USER"


def test_user_list_response():
    resp = AdminUserListResponse(users=[], total=0, page=1, per_page=20)
    assert resp.total == 0
