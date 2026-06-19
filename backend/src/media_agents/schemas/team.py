import uuid
from typing import List, Optional

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
