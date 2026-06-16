import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from media_agents.auth.dependencies import get_current_user
from media_agents.services import agent as agent_service
from media_agents.analytics import analytics
from media_agents.analytics.events import AGENT_CREATED, AGENT_DELETED

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: str
    board_id: Optional[uuid.UUID] = None
    config: Optional[Dict[str, Any]] = None
    # Analytics hint — the frontend can set this to distinguish template vs
    # freeform prompt vs slash-command creation paths. Defaults to
    # "custom_prompt" when omitted. Purely informational; not persisted.
    creation_source: Optional[str] = None
    template_key: Optional[str] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    system_prompt: str
    board_id: Optional[str]
    config: Dict[str, Any]
    created_at: str
    updated_at: str


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]


def _format_datetime(dt: datetime) -> str:
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


@router.get("", response_model=AgentListResponse)
async def list_agents(
    board_id: Optional[uuid.UUID] = None,
    global_only: bool = False,
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["id"])
    if global_only:
        agents = await agent_service.get_global_agents(user_id)
    elif board_id:
        agents = await agent_service.get_agents_by_board(board_id, user_id)
    else:
        agents = await agent_service.get_agents_by_user(user_id)
    return AgentListResponse(
        agents=[
            AgentResponse(
                id=a["id"],
                name=a["name"],
                description=a.get("description"),
                system_prompt=a["systemPrompt"],
                board_id=a.get("boardId"),
                config=a.get("config", {}),
                created_at=_format_datetime(a["createdAt"]),
                updated_at=_format_datetime(a["updatedAt"]),
            )
            for a in agents
        ]
    )


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: AgentCreate,
    current_user: dict = Depends(get_current_user),
):
    agent = await agent_service.create_agent(
        uuid.UUID(current_user["id"]),
        data.name,
        data.system_prompt,
        data.board_id,
        data.description,
        data.config,
    )
    source = (
        data.creation_source
        if data.creation_source in {"template", "custom_prompt", "slash_command"}
        else "custom_prompt"
    )
    analytics.capture(
        user_id=current_user["id"],
        event=AGENT_CREATED,
        email=current_user.get("email"),
        properties={
            "agent_id": agent["id"],
            "creation_source": source,
            "template_key": data.template_key,
            "scope": "board" if agent.get("boardId") else "global",
        },
    )
    return AgentResponse(
        id=agent["id"],
        name=agent["name"],
        description=agent.get("description"),
        system_prompt=agent["systemPrompt"],
        board_id=agent.get("boardId"),
        config=agent.get("config", {}),
        created_at=_format_datetime(agent["createdAt"]),
        updated_at=_format_datetime(agent["updatedAt"]),
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    agent = await agent_service.get_agent_by_id(agent_id, uuid.UUID(current_user["id"]))
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )
    return AgentResponse(
        id=agent["id"],
        name=agent["name"],
        description=agent.get("description"),
        system_prompt=agent["systemPrompt"],
        board_id=agent.get("boardId"),
        config=agent.get("config", {}),
        created_at=_format_datetime(agent["createdAt"]),
        updated_at=_format_datetime(agent["updatedAt"]),
    )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    data: AgentUpdate,
    current_user: dict = Depends(get_current_user),
):
    agent = await agent_service.get_agent_by_id(agent_id, uuid.UUID(current_user["id"]))
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )
    updated = await agent_service.update_agent(
        agent_id,
        uuid.UUID(current_user["id"]),
        data.name,
        data.description,
        data.system_prompt,
        data.config,
    )
    return AgentResponse(
        id=updated["id"],
        name=updated["name"],
        description=updated.get("description"),
        system_prompt=updated["systemPrompt"],
        board_id=updated.get("boardId"),
        config=updated.get("config", {}),
        created_at=_format_datetime(updated["createdAt"]),
        updated_at=_format_datetime(updated["updatedAt"]),
    )


@router.get("/models/openrouter", response_model=list[str])
async def list_openrouter_models(
    current_user: dict = Depends(get_current_user),
):
    """Proxy OpenRouter's public model list to avoid browser CORS restrictions."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get("https://openrouter.ai/api/v1/models")
        resp.raise_for_status()
    ids: list[str] = sorted(m["id"] for m in resp.json().get("data", []))
    return ids


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    agent = await agent_service.get_agent_by_id(agent_id, uuid.UUID(current_user["id"]))
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )
    created = agent.get("createdAt")
    age_days = 0
    if hasattr(created, "date"):
        age_days = max(0, (datetime.now(created.tzinfo).date() - created.date()).days)
    await agent_service.delete_agent(agent_id)
    analytics.capture(
        user_id=current_user["id"],
        event=AGENT_DELETED,
        email=current_user.get("email"),
        properties={"agent_id": str(agent_id), "age_days": age_days},
    )
