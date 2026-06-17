"""Tests for admin service — input validation and logging."""

from __future__ import annotations


import pytest
from fastapi import HTTPException

from media_agents.services.admin import (
    validate_tier,
    validate_role,
    validate_credits_input,
    VALID_TIERS,
    VALID_ROLES,
)


def test_valid_tiers_match_schema():
    assert "FREE_TRIAL" in VALID_TIERS
    assert "STARTER" in VALID_TIERS
    assert "PLUS" in VALID_TIERS
    assert "PRO" in VALID_TIERS
    assert "ENTERPRISE" in VALID_TIERS


def test_valid_roles_match_schema():
    assert "USER" in VALID_ROLES
    assert "ADMIN" in VALID_ROLES
    assert "SUPER_ADMIN" in VALID_ROLES


def test_validate_tier_accepts_valid():
    validate_tier("PLUS")  # should not raise


def test_validate_tier_rejects_invalid():
    with pytest.raises(HTTPException) as exc_info:
        validate_tier("GOLD")
    assert exc_info.value.status_code == 400


def test_validate_role_accepts_valid():
    validate_role("ADMIN")  # should not raise


def test_validate_role_rejects_invalid():
    with pytest.raises(HTTPException) as exc_info:
        validate_role("MODERATOR")
    assert exc_info.value.status_code == 400


def test_validate_credits_rejects_both_none():
    with pytest.raises(HTTPException) as exc_info:
        validate_credits_input(None, None)
    assert exc_info.value.status_code == 400


def test_validate_credits_rejects_negative_subscription():
    with pytest.raises(HTTPException) as exc_info:
        validate_credits_input(-5, None)
    assert exc_info.value.status_code == 400


def test_validate_credits_rejects_negative_pack():
    with pytest.raises(HTTPException) as exc_info:
        validate_credits_input(None, -10)
    assert exc_info.value.status_code == 400


def test_validate_credits_accepts_valid():
    validate_credits_input(100, 50)  # should not raise


def test_validate_credits_accepts_zero():
    validate_credits_input(0, 0)  # should not raise
