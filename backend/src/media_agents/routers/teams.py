import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from media_agents.schemas.team import TeamCreate, TeamUpdate

from media_agents.auth.dependencies import get_current_user
from media_agents.services import team as team_service
from media_agents.analytics import analytics
from media_agents.analytics.events import TEAM_CREATED, TEAM_DELETED

from media_agents.schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamListResponse,
)


router = APIRouter(prefix="/teams", tags=["teams"])
router = APIRouter(prefix="/teams", tags=["teams"])


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


def _format_datetime(dt: datetime) -> str:
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


def _to_response(t: dict) -> TeamResponse:
    return TeamResponse(
        id=t["id"],
        name=t["name"],
        description=t.get("description"),
        board_id=t.get("boardId"),
        members=t.get("members", {}) or {},
        orchestrator=t.get("orchestrator", {}) or {},
        created_at=_format_datetime(t["createdAt"]),
        updated_at=_format_datetime(t["updatedAt"]),
    )


@router.get("", response_model=TeamListResponse)
async def list_teams(
    board_id: Optional[uuid.UUID] = None,
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["id"])
    if board_id:
        teams = await team_service.get_teams_by_board(board_id, user_id)
    else:
        teams = await team_service.get_teams_by_user(user_id)
    return TeamListResponse(teams=[_to_response(t) for t in teams])


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    data: TeamCreate,
    current_user: dict = Depends(get_current_user),
):
    team = await team_service.create_team(
        uuid.UUID(current_user["id"]),
        data,
    )
    members = team.get("members") or {}
    member_count = len(members.get("agent_ids") or []) + len(
        members.get("capabilities") or []
    )
    analytics.capture(
        user_id=current_user["id"],
        event=TEAM_CREATED,
        email=current_user.get("email"),
        properties={
            "team_id": team["id"],
            "member_count": member_count,
            "scope": "board" if team.get("boardId") else "global",
        },
    )
    return _to_response(team)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    team = await team_service.get_team_by_id(team_id, uuid.UUID(current_user["id"]))
    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )
    return _to_response(team)


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: uuid.UUID,
    data: TeamUpdate,
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["id"])
    existing = await team_service.get_team_by_id(team_id, user_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )
    updated = await team_service.update_team(
        team_id,
        user_id,
        data,
    )
    return _to_response(updated)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    team = await team_service.get_team_by_id(team_id, uuid.UUID(current_user["id"]))
    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )
    created = team.get("createdAt")
    age_days = 0
    if hasattr(created, "date"):
        age_days = max(0, (datetime.now(created.tzinfo).date() - created.date()).days)
    await team_service.delete_team(team_id)
    analytics.capture(
        user_id=current_user["id"],
        event=TEAM_DELETED,
        email=current_user.get("email"),
        properties={"team_id": str(team_id), "age_days": age_days},
    )
