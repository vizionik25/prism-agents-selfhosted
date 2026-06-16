"""Admin endpoints — internal user management.

All endpoints require ADMIN or SUPER_ADMIN role. JWT auth only.
"""

from __future__ import annotations

import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from media_agents.auth.dependencies import require_admin, require_super_admin
from media_agents.services import admin as admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


class ChangeTierRequest(BaseModel):
    tier: str = Field(...)


class GrantCreditsRequest(BaseModel):
    subscription_credits: Optional[int] = None
    pack_credits: Optional[int] = None


class ChangeRoleRequest(BaseModel):
    role: str = Field(...)


class AdminUserSummary(BaseModel):
    id: str
    username: str
    email: str
    role: str
    subscription_tier: str
    subscription_credits: int
    pack_credits: int
    created_at: Optional[str]


class AdminApiKey(BaseModel):
    id: str
    name: str
    key_prefix: str
    created_at: Optional[str]
    last_used_at: Optional[str]
    revoked_at: Optional[str]


class AdminUserDetail(AdminUserSummary):
    avatar_url: Optional[str]
    credits_reset_at: Optional[str]
    stripe_customer_id: Optional[str]
    api_keys: List[AdminApiKey] = []


class AdminUserListResponse(BaseModel):
    users: List[AdminUserSummary]
    total: int
    page: int
    per_page: int


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    search: str = Query("", description="Filter by email or username"),
    tier: Optional[str] = Query(None, description="Filter by subscription tier"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_admin),
):
    return await admin_service.list_users(search, tier, page, per_page)


@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def get_user_detail(
    user_id: uuid.UUID,
    current_user: dict = Depends(require_admin),
):
    return await admin_service.get_user_detail(user_id)


@router.patch("/users/{user_id}/tier", response_model=AdminUserSummary)
async def change_tier(
    user_id: uuid.UUID,
    body: ChangeTierRequest,
    current_user: dict = Depends(require_admin),
):
    return await admin_service.change_tier(user_id, body.tier, current_user["id"])


@router.patch("/users/{user_id}/credits", response_model=AdminUserSummary)
async def grant_credits(
    user_id: uuid.UUID,
    body: GrantCreditsRequest,
    current_user: dict = Depends(require_admin),
):
    return await admin_service.grant_credits(
        user_id, body.subscription_credits, body.pack_credits, current_user["id"]
    )


@router.patch("/users/{user_id}/role", response_model=AdminUserSummary)
async def change_role(
    user_id: uuid.UUID,
    body: ChangeRoleRequest,
    current_user: dict = Depends(require_super_admin),
):
    return await admin_service.change_role(user_id, body.role, current_user["id"])


@router.delete(
    "/users/{user_id}/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_user_api_key(
    user_id: uuid.UUID,
    key_id: uuid.UUID,
    current_user: dict = Depends(require_admin),
):
    await admin_service.admin_revoke_api_key(user_id, key_id, current_user["id"])
