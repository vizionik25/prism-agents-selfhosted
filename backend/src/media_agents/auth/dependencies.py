from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from media_agents.auth.jwt import decode_token
from media_agents.env import DEMO_MODE, SELF_HOSTED
from media_agents.services import user as user_service
from media_agents.services import api_key as api_key_service
from media_agents.services.api_key import API_KEY_PREFIX, ALLOWED_TIERS

security = HTTPBearer(auto_error=not DEMO_MODE)

DEMO_USER: dict = {
    "id": "00000000-0000-0000-0000-000000000000",
    "githubId": "demo",
    "username": "Demo User",
    "email": "demo@prismagents.com",
    "avatarUrl": None,
    "accessToken": None,
    "subscriptionTier": "PRO",
    "subscriptionCredits": 999999,
    "packCredits": 999999,
    "creditsResetAt": None,
    "stripeCustomerId": None,
    "stripeSubscriptionId": None,
}


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    if DEMO_MODE:
        return DEMO_USER

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = credentials.credentials

    # --- API key path ---
    if token.startswith(API_KEY_PREFIX):
        user = await api_key_service.lookup_by_raw_key(token)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key",
            )
        if SELF_HOSTED:
            from media_agents.services.license import LicenseService

            if not LicenseService.has_enterprise_license():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API key access requires a self-hosted Enterprise license.",
                )
        else:
            tier = user.get("subscriptionTier", "FREE_TRIAL")
            if hasattr(tier, "value"):
                tier = tier.value
            if tier not in ALLOWED_TIERS:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API key access requires a Plus or higher subscription.",
                )
        user["is_api_key"] = True
        return user

    # --- JWT path (existing) ---
    user_id = decode_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = await user_service.get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[dict]:
    if DEMO_MODE:
        return DEMO_USER

    if credentials is None:
        return None

    token = credentials.credentials

    if token.startswith(API_KEY_PREFIX):
        user = await api_key_service.lookup_by_raw_key(token)
        if user is None:
            return None
        if SELF_HOSTED:
            from media_agents.services.license import LicenseService

            if not LicenseService.has_enterprise_license():
                return None
        else:
            tier = user.get("subscriptionTier", "FREE_TRIAL")
            if hasattr(tier, "value"):
                tier = tier.value
            if tier not in ALLOWED_TIERS:
                return None
        user["is_api_key"] = True
        return user

    user_id = decode_token(token)
    if user_id is None:
        return None

    return await user_service.get_user_by_id(user_id)


async def require_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Require ADMIN or SUPER_ADMIN role. Rejects API key auth."""
    if current_user.get("is_api_key"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key auth not allowed for admin endpoints",
        )
    role = current_user.get("role", "USER")
    if hasattr(role, "value"):
        role = role.value
    if role not in ("ADMIN", "SUPER_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_super_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Require SUPER_ADMIN role. Rejects API key auth."""
    if current_user.get("is_api_key"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key auth not allowed for admin endpoints",
        )
    role = current_user.get("role", "USER")
    if hasattr(role, "value"):
        role = role.value
    if role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user
