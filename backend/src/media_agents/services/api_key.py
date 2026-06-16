"""API key management — generation, hashing, CRUD operations.

Keys are generated as ``sk-prism-<random>`` and only the SHA-256 hash is
persisted.  The raw key is returned once at creation and never stored.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from media_agents.prisma import prisma
from media_agents.services.user import _to_dict
from media_agents.env import SELF_HOSTED

API_KEY_PREFIX = "sk-prism-"
MAX_KEYS_PER_USER = 10

DISCLAIMER_TEXT = (
    "By generating an API key, you acknowledge that: "
    "(1) Automated systems and external agents can consume credits significantly "
    "faster than manual usage through the web interface. "
    "(2) You are solely responsible for managing and monitoring your credit usage "
    "when using API access. "
    "(3) Credit usage management features (daily/weekly/monthly limits) are not yet "
    "available. You should monitor your credit balance regularly. "
    "(4) PrismAgents is not responsible for excessive credit consumption resulting "
    "from automated or programmatic usage. "
    "(5) API keys grant full access to your account's capabilities. Keep them secret "
    "and revoke any compromised keys immediately."
)

ALLOWED_TIERS = {"PLUS", "PRO", "ENTERPRISE"}


def generate_raw_key() -> str:
    random_part = secrets.token_urlsafe(32)
    return f"{API_KEY_PREFIX}{random_part}"


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def key_prefix(raw_key: str) -> str:
    return raw_key[:12] + "..."


def _check_tier(user: dict) -> None:
    if SELF_HOSTED:
        from media_agents.services.license import LicenseService
        if not LicenseService.has_enterprise_license():
            raise HTTPException(
                status_code=403,
                detail="API key access requires a self-hosted Enterprise license.",
            )
    else:
        tier = user.get("subscriptionTier", "FREE_TRIAL")
        if hasattr(tier, "value"):
            tier = tier.value
        if tier not in ALLOWED_TIERS:
            raise HTTPException(
                status_code=403,
                detail="API key access requires a Plus or higher subscription.",
            )


async def create_api_key(
    user_id: uuid.UUID,
    name: str,
    agreed_to_disclaimer: bool,
    user: dict,
) -> tuple[dict, str]:
    _check_tier(user)
    name = name.strip()
    if not name or len(name) > 64:
        raise HTTPException(
            status_code=400,
            detail="Key name must be between 1 and 64 characters.",
        )
    has_prior_agreement = user.get("apiDisclaimerAgreedAt") is not None
    if not has_prior_agreement and not agreed_to_disclaimer:
        raise HTTPException(
            status_code=400,
            detail="You must agree to the API access disclaimer before creating your first key.",
        )
    active_count = await prisma.apikey.count(
        where={"userId": str(user_id), "revokedAt": None},
    )
    if active_count >= MAX_KEYS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {MAX_KEYS_PER_USER} active API keys allowed.",
        )
    raw = generate_raw_key()
    hashed = hash_key(raw)
    prefix = key_prefix(raw)
    if not has_prior_agreement and agreed_to_disclaimer:
        await prisma.user.update(
            where={"id": str(user_id)},
            data={"apiDisclaimerAgreedAt": datetime.now(timezone.utc)},
        )
    record = await prisma.apikey.create(
        data={
            "userId": str(user_id),
            "name": name,
            "keyHash": hashed,
            "keyPrefix": prefix,
            "agreedToDisclaimer": agreed_to_disclaimer or has_prior_agreement,
        },
    )
    return record.model_dump(), raw


async def list_api_keys(user_id: uuid.UUID) -> list[dict]:
    keys = await prisma.apikey.find_many(
        where={"userId": str(user_id)},
        order={"createdAt": "desc"},
    )
    return [k.model_dump() for k in keys]


async def revoke_api_key(key_id: uuid.UUID, user_id: uuid.UUID) -> None:
    key = await prisma.apikey.find_first(
        where={"id": str(key_id), "userId": str(user_id)},
    )
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found.")
    if key.revokedAt is not None:
        raise HTTPException(status_code=400, detail="API key is already revoked.")
    await prisma.apikey.update(
        where={"id": str(key_id)},
        data={"revokedAt": datetime.now(timezone.utc)},
    )


async def lookup_by_raw_key(raw_key: str) -> Optional[dict]:
    hashed = hash_key(raw_key)
    record = await prisma.apikey.find_first(
        where={"keyHash": hashed, "revokedAt": None},
        include={"user": True},
    )
    if record is None:
        return None
    await prisma.apikey.update(
        where={"id": record.id},
        data={"lastUsedAt": datetime.now(timezone.utc)},
    )
    user = record.user
    if user is None:
        return None
    return _to_dict(user)
