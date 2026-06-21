"""Admin service — user management operations with audit logging.

All mutating operations log an ADMIN_ACTION entry for auditability.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from media_agents.prisma import prisma
from media_agents.services.credits import reset_subscription_credits, add_pack_credits

logger = logging.getLogger(__name__)

VALID_TIERS = {"FREE_TRIAL", "STARTER", "PLUS", "PRO", "ENTERPRISE"}
VALID_ROLES = {"USER", "ADMIN", "SUPER_ADMIN"}


def validate_tier(tier: str) -> None:
    if tier not in VALID_TIERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier. Must be one of: {', '.join(sorted(VALID_TIERS))}",
        )


def validate_role(role: str) -> None:
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}",
        )


def validate_credits_input(
    subscription_credits: Optional[int],
    pack_credits: Optional[int],
) -> None:
    if subscription_credits is None and pack_credits is None:
        raise HTTPException(
            status_code=400,
            detail="At least one of subscription_credits or pack_credits must be provided.",
        )
    if subscription_credits is not None and subscription_credits < 0:
        raise HTTPException(
            status_code=400, detail="subscription_credits cannot be negative."
        )
    if pack_credits is not None and pack_credits < 0:
        raise HTTPException(status_code=400, detail="pack_credits cannot be negative.")


def _user_to_summary(user) -> dict:
    """Convert a Prisma user record to a summary dict for list responses."""
    tier = (
        user.subscriptionTier.value
        if hasattr(user.subscriptionTier, "value")
        else str(user.subscriptionTier)
    )
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": role,
        "subscription_tier": tier,
        "subscription_credits": user.subscriptionCredits or 0,
        "pack_credits": user.packCredits or 0,
        "created_at": user.createdAt.isoformat() if user.createdAt else None,
    }


def _user_to_detail(user, api_keys=None) -> dict:
    """Convert a Prisma user record to a detail dict."""
    result = _user_to_summary(user)
    result["avatar_url"] = user.avatarUrl
    result["credits_reset_at"] = (
        user.creditsResetAt.isoformat() if user.creditsResetAt else None
    )
    result["stripe_customer_id"] = user.stripeCustomerId
    if api_keys is not None:
        result["api_keys"] = [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.keyPrefix,
                "created_at": k.createdAt.isoformat() if k.createdAt else None,
                "last_used_at": k.lastUsedAt.isoformat() if k.lastUsedAt else None,
                "revoked_at": k.revokedAt.isoformat() if k.revokedAt else None,
            }
            for k in api_keys
        ]
    return result


async def list_users(
    search: str = "",
    tier: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """Paginated user list with optional search and tier filter."""
    per_page = min(per_page, 100)
    skip = (page - 1) * per_page

    where = {}
    conditions = []
    if search:
        conditions.append(
            {
                "OR": [
                    {"username": {"contains": search, "mode": "insensitive"}},
                    {"email": {"contains": search, "mode": "insensitive"}},
                ]
            }
        )
    if tier:
        validate_tier(tier)
        conditions.append({"subscriptionTier": tier})
    if conditions:
        where = {"AND": conditions} if len(conditions) > 1 else conditions[0]

    total = await prisma.user.count(where=where)
    users = await prisma.user.find_many(
        where=where,
        skip=skip,
        take=per_page,
        order={"createdAt": "desc"},
    )

    return {
        "users": [_user_to_summary(u) for u in users],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


async def get_user_detail(user_id: uuid.UUID) -> dict:
    """Full user detail including API keys."""
    user = await prisma.user.find_unique(
        where={"id": str(user_id)},
        include={"apiKeys": True},
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_detail(user, api_keys=user.apiKeys or [])


async def change_tier(
    user_id: uuid.UUID,
    new_tier: str,
    admin_id: str,
) -> dict:
    """Change a user's subscription tier and reset credits."""
    validate_tier(new_tier)

    user = await prisma.user.find_unique(where={"id": str(user_id)})
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    old_tier = (
        user.subscriptionTier.value
        if hasattr(user.subscriptionTier, "value")
        else str(user.subscriptionTier)
    )

    # Update user and reset credits
    await prisma.user.update(
        where={"id": str(user_id)},
        data={"subscriptionTier": new_tier},
    )

    # reset_subscription_credits performs an update and returns the user dict
    updated = await reset_subscription_credits(user_id, known_tier=new_tier)

    logger.info(
        "ADMIN_ACTION: %s changed tier for %s: %s -> %s",
        admin_id,
        str(user_id),
        old_tier,
        new_tier,
    )

    return _user_to_summary(updated) if updated else {}


async def grant_credits(
    user_id: uuid.UUID,
    subscription_credits: Optional[int],
    pack_credits: Optional[int],
    admin_id: str,
) -> dict:
    """Grant credits to a user."""
    validate_credits_input(subscription_credits, pack_credits)

    user = await prisma.user.find_unique(where={"id": str(user_id)})
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    updated = user

    # We update subscriptionCredits directly
    if subscription_credits is not None:
        updated = await prisma.user.update(
            where={"id": str(user_id)},
            data={"subscriptionCredits": subscription_credits},
        )
        logger.info(
            "ADMIN_ACTION: %s set subscription_credits for %s to %d",
            admin_id,
            str(user_id),
            subscription_credits,
        )

    # We use add_pack_credits to preserve its specific behavior/logging instead of combining it into the first query.
    if pack_credits is not None and pack_credits > 0:
        updated = await add_pack_credits(user_id, pack_credits)
        logger.info(
            "ADMIN_ACTION: %s added %d pack_credits to %s",
            admin_id,
            pack_credits,
            str(user_id),
        )

    return _user_to_summary(updated) if updated else {}


async def change_role(
    user_id: uuid.UUID,
    new_role: str,
    admin_id: str,
) -> dict:
    """Change a user's role. Cannot self-demote."""
    validate_role(new_role)

    if str(user_id) == admin_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot change your own role.",
        )

    user = await prisma.user.find_unique(where={"id": str(user_id)})
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = user.role.value if hasattr(user.role, "value") else str(user.role)

    updated = await prisma.user.update(
        where={"id": str(user_id)},
        data={"role": new_role},
    )

    logger.info(
        "ADMIN_ACTION: %s changed role for %s: %s -> %s",
        admin_id,
        str(user_id),
        old_role,
        new_role,
    )

    return _user_to_summary(updated) if updated else {}


async def admin_revoke_api_key(
    user_id: uuid.UUID,
    key_id: uuid.UUID,
    admin_id: str,
) -> None:
    """Revoke a user's API key (admin action)."""
    key = await prisma.apikey.find_first(
        where={"id": str(key_id), "userId": str(user_id)},
    )
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    if key.revokedAt is not None:
        raise HTTPException(status_code=400, detail="API key is already revoked")

    await prisma.apikey.update(
        where={"id": str(key_id)},
        data={"revokedAt": datetime.now(timezone.utc)},
    )

    logger.info(
        "ADMIN_ACTION: %s revoked API key %s for user %s",
        admin_id,
        str(key_id),
        str(user_id),
    )
