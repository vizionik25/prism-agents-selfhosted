import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TeamMembers(BaseModel):
    capabilities: List[str] = []
    agent_ids: List[str] = []


class TeamOrchestrator(BaseModel):
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    routing_strategy: Optional[str] = None
    max_credits: Optional[int] = None


class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None
    board_id: Optional[uuid.UUID] = None
    members: Optional[TeamMembers] = None
    orchestrator: Optional[TeamOrchestrator] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    members: Optional[TeamMembers] = None
    orchestrator: Optional[TeamOrchestrator] = None


class TeamResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    board_id: Optional[str]
    members: Dict[str, Any]
    orchestrator: Dict[str, Any]
    created_at: str
    updated_at: str


class TeamListResponse(BaseModel):
    teams: List[TeamResponse]
