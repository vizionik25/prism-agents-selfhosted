from fastapi import APIRouter, Depends, HTTPException, status
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from media_agents.auth.dependencies import get_current_user
from media_agents.services import generation as generation_service
from pydantic import BaseModel

router = APIRouter(prefix="/generations", tags=["generations"])


class VariantResponse(BaseModel):
    id: str
    variant_index: int
    result_url: Optional[str]
    result_type: Optional[str]
    metadata: Dict[str, Any]
    created_at: str


class GenerationResponse(BaseModel):
    id: str
    board_id: str
    agent_id: Optional[str]
    prompt: str
    status: str
    result_url: Optional[str]
    result_type: Optional[str]
    metadata: Dict[str, Any]
    variants: List[VariantResponse]
    created_at: str


class GenerationListResponse(BaseModel):
    generations: list[GenerationResponse]


def _format_datetime(dt: datetime) -> str:
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


def _format_status(status: str) -> str:
    # DB stores the Prisma GenerationStatus enum in uppercase (PENDING/PROCESSING/
    # COMPLETED/FAILED); API contract (TypeScript type and SSE `status` event) uses
    # lowercase. Normalize at the boundary.
    return status.lower() if isinstance(status, str) else str(status).lower()


@router.get("", response_model=GenerationListResponse)
async def list_generations(
    board_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    generations = await generation_service.get_generations_by_board(
        board_id, uuid.UUID(current_user["id"])
    )
    return GenerationListResponse(
        generations=[
            GenerationResponse(
                id=g["id"],
                board_id=g["boardId"],
                agent_id=g.get("agentId"),
                prompt=g["prompt"],
                status=_format_status(g["status"]),
                result_url=g.get("resultUrl"),
                result_type=g.get("resultType"),
                metadata=g.get("metadata", {}),
                variants=[
                    VariantResponse(
                        id=v["id"],
                        variant_index=v["variantIndex"],
                        result_url=v.get("resultUrl"),
                        result_type=v.get("resultType"),
                        metadata=v.get("metadata", {}),
                        created_at=_format_datetime(v["createdAt"]),
                    )
                    for v in sorted(
                        g.get("variants", []), key=lambda x: x["variantIndex"]
                    )
                ],
                created_at=_format_datetime(g["createdAt"]),
            )
            for g in generations
        ]
    )


@router.get("/{generation_id}", response_model=GenerationResponse)
async def get_generation(
    generation_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    generation = await generation_service.get_generation_by_id(
        generation_id, uuid.UUID(current_user["id"])
    )
    if generation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found"
        )
    return GenerationResponse(
        id=generation["id"],
        board_id=generation["boardId"],
        agent_id=generation.get("agentId"),
        prompt=generation["prompt"],
        status=_format_status(generation["status"]),
        result_url=generation.get("resultUrl"),
        result_type=generation.get("resultType"),
        metadata=generation.get("metadata", {}),
        variants=[
            VariantResponse(
                id=v["id"],
                variant_index=v["variantIndex"],
                result_url=v.get("resultUrl"),
                result_type=v.get("resultType"),
                metadata=v.get("metadata", {}),
                created_at=_format_datetime(v["createdAt"]),
            )
            for v in sorted(
                generation.get("variants", []), key=lambda x: x["variantIndex"]
            )
        ],
        created_at=_format_datetime(generation["createdAt"]),
    )


@router.delete("/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generation(
    generation_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    generation = await generation_service.get_generation_by_id(
        generation_id, uuid.UUID(current_user["id"])
    )
    if generation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found"
        )
    await generation_service.delete_generation(generation_id)
