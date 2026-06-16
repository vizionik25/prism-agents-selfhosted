import uuid
from typing import Optional, Dict, Any, List

from prisma import Json

from media_agents.prisma import prisma


async def get_generations_by_board(
    board_id: uuid.UUID, user_id: uuid.UUID
) -> List[dict]:
    generations = await prisma.generation.find_many(
        where={"boardId": str(board_id), "userId": str(user_id)},
        include={"variants": {"orderBy": {"variantIndex": "asc"}}},
        order={"createdAt": "desc"},
    )
    return [gen.model_dump() for gen in generations]


async def get_generation_by_id(
    generation_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[dict]:
    generation = await prisma.generation.find_unique(
        where={"id": str(generation_id)},
        include={"variants": {"orderBy": {"variantIndex": "asc"}}},
    )
    if generation and generation.userId == str(user_id):
        return generation.model_dump()
    return None


async def create_generation(
    user_id: uuid.UUID,
    board_id: uuid.UUID,
    prompt: str,
    agent_id: Optional[uuid.UUID] = None,
    status: str = "PENDING",
) -> dict:
    generation = await prisma.generation.create(
        data={
            "userId": str(user_id),
            "boardId": str(board_id),
            "agentId": str(agent_id) if agent_id else None,
            "prompt": prompt,
            "status": status,
        }
    )
    return generation.model_dump()


async def update_generation(
    generation_id: uuid.UUID,
    status: Optional[str] = None,
    result_url: Optional[str] = None,
    result_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[dict]:
    generation = await prisma.generation.find_unique(where={"id": str(generation_id)})
    if not generation:
        return None

    update_data = {}
    if status is not None:
        update_data["status"] = status
    if result_url is not None:
        update_data["resultUrl"] = result_url
    if result_type is not None:
        update_data["resultType"] = result_type
    if metadata is not None:
        update_data["metadata"] = Json(metadata)

    updated = await prisma.generation.update(
        where={"id": str(generation_id)},
        data=update_data,
    )
    return updated.model_dump()


async def add_variants(
    generation_id: uuid.UUID,
    variants_data: List[Dict[str, Any]],
) -> int:
    data = []
    for variant in variants_data:
        data.append(
            {
                "generationId": str(generation_id),
                "variantIndex": variant["variant_index"],
                "resultUrl": variant.get("result_url"),
                "resultType": variant.get("result_type"),
                "metadata": Json(variant.get("metadata", {})),
            }
        )
    result = await prisma.generationvariant.create_many(data=data)
    return result


async def add_variant(
    generation_id: uuid.UUID,
    variant_index: int,
    result_url: Optional[str] = None,
    result_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> dict:
    variant = await prisma.generationvariant.create(
        data={
            "generationId": str(generation_id),
            "variantIndex": variant_index,
            "resultUrl": result_url,
            "resultType": result_type,
            "metadata": Json(metadata or {}),
        }
    )
    return variant.model_dump()


async def delete_generation(generation_id: uuid.UUID) -> None:
    await prisma.generation.delete(where={"id": str(generation_id)})
