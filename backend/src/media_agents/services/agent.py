import uuid
from typing import Optional, Dict, Any, List

from prisma import Json

from media_agents.prisma import prisma


async def get_agents_by_user(user_id: uuid.UUID) -> List[dict]:
    agents = await prisma.agent.find_many(
        where={"userId": str(user_id), "isActive": True},
        order={"updatedAt": "desc"},
    )
    return [agent.model_dump() for agent in agents]


async def get_global_agents(user_id: uuid.UUID) -> List[dict]:
    """Return agents that belong to the user but are not tied to any board."""
    agents = await prisma.agent.find_many(
        where={"userId": str(user_id), "boardId": None, "isActive": True},
        order={"updatedAt": "desc"},
    )
    return [agent.model_dump() for agent in agents]


async def get_agents_by_board(board_id: uuid.UUID, user_id: uuid.UUID) -> List[dict]:
    agents = await prisma.agent.find_many(
        where={
            "boardId": str(board_id),
            "userId": str(user_id),
            "isActive": True,
        },
        order={"updatedAt": "desc"},
    )
    return [agent.model_dump() for agent in agents]


async def get_agent_by_id(agent_id: uuid.UUID, user_id: uuid.UUID) -> Optional[dict]:
    agent = await prisma.agent.find_unique(
        where={"id": str(agent_id)},
    )
    if agent and agent.userId == str(user_id):
        return agent.model_dump()
    return None


async def create_agent(
    user_id: uuid.UUID,
    name: str,
    system_prompt: str,
    board_id: Optional[uuid.UUID] = None,
    description: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> dict:
    agent = await prisma.agent.create(
        data={
            "userId": str(user_id),
            "boardId": str(board_id) if board_id else None,
            "name": name,
            "description": description,
            "systemPrompt": system_prompt,
            "config": Json(config or {}),
        }
    )
    return agent.model_dump()


async def update_agent(
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    system_prompt: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Optional[dict]:
    agent = await get_agent_by_id(agent_id, user_id)
    if not agent:
        return None

    update_data: dict = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if system_prompt is not None:
        update_data["systemPrompt"] = system_prompt
    if config is not None:
        update_data["config"] = Json(config)

    updated = await prisma.agent.update(
        where={"id": str(agent_id)},
        data=update_data,
    )
    return updated.model_dump()


async def delete_agent(agent_id: uuid.UUID) -> None:
    await prisma.agent.update(
        where={"id": str(agent_id)},
        data={"isActive": False},
    )
