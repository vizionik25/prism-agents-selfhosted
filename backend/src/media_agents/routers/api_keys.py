"""API key management endpoints.

All endpoints require JWT auth — API keys cannot manage other API keys.
"""

from __future__ import annotations

import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from media_agents.auth.dependencies import get_current_user
from media_agents.services import api_key as api_key_service

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    agreed_to_disclaimer: bool = False


class ApiKeyCreatedResponse(BaseModel):
    id: str
    name: str
    key: str
    key_prefix: str
    created_at: str


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    created_at: str
    last_used_at: Optional[str]
    revoked_at: Optional[str]


class ApiKeyListResponse(BaseModel):
    keys: List[ApiKeyResponse]


def _format_dt(dt) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: CreateApiKeyRequest,
    current_user: dict = Depends(get_current_user),
):
    record, raw_key = await api_key_service.create_api_key(
        user_id=uuid.UUID(current_user["id"]),
        name=body.name,
        agreed_to_disclaimer=body.agreed_to_disclaimer,
        user=current_user,
    )
    return ApiKeyCreatedResponse(
        id=record["id"],
        name=record["name"],
        key=raw_key,
        key_prefix=record["keyPrefix"],
        created_at=_format_dt(record["createdAt"]),
    )


@router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(
    current_user: dict = Depends(get_current_user),
):
    keys = await api_key_service.list_api_keys(uuid.UUID(current_user["id"]))
    return ApiKeyListResponse(
        keys=[
            ApiKeyResponse(
                id=k["id"],
                name=k["name"],
                key_prefix=k["keyPrefix"],
                created_at=_format_dt(k["createdAt"]),
                last_used_at=_format_dt(k.get("lastUsedAt")),
                revoked_at=_format_dt(k.get("revokedAt")),
            )
            for k in keys
        ]
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    await api_key_service.revoke_api_key(key_id, uuid.UUID(current_user["id"]))
