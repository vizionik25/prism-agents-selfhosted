"""Build identify() payloads from a User row."""

from __future__ import annotations
from typing import Any

from .client import is_internal_email


def _tier_value(tier: Any) -> str:
    if hasattr(tier, "value"):
        return tier.value
    return str(tier or "FREE_TRIAL")


def _isoformat(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def full_identify_payload(user: dict[str, Any]) -> dict[str, Any]:
    """Full trait set — used on signup and by the daily reconciliation job."""
    sub = user.get("subscriptionCredits") or 0
    pack = user.get("packCredits") or 0
    return {
        "email": user.get("email"),
        "username": user.get("username"),
        "github_id": user.get("githubId"),
        "created_at": _isoformat(user.get("createdAt")),
        "subscription_tier": _tier_value(user.get("subscriptionTier")),
        "subscription_credits": sub,
        "pack_credits": pack,
        "credits_total": sub + pack,
        "credits_reset_at": _isoformat(user.get("creditsResetAt")),
        "is_internal": is_internal_email(user.get("email")),
    }


def signin_traits(user: dict[str, Any]) -> dict[str, Any]:
    """Lean payload refreshed on every sign-in."""
    sub = user.get("subscriptionCredits") or 0
    pack = user.get("packCredits") or 0
    return {
        "subscription_tier": _tier_value(user.get("subscriptionTier")),
        "subscription_credits": sub,
        "pack_credits": pack,
        "credits_total": sub + pack,
    }


def credit_traits(user: dict[str, Any]) -> dict[str, Any]:
    sub = user.get("subscriptionCredits") or 0
    pack = user.get("packCredits") or 0
    return {
        "subscription_credits": sub,
        "pack_credits": pack,
        "credits_total": sub + pack,
    }


def tier_traits(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "subscription_tier": _tier_value(user.get("subscriptionTier")),
        "credits_reset_at": _isoformat(user.get("creditsResetAt")),
    }
