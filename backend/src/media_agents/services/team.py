import uuid
from typing import List, Optional

from prisma import Json

from media_agents.schemas.team import TeamCreate, TeamUpdate
from media_agents.prisma import prisma


async def get_teams_by_user(user_id: uuid.UUID) -> List[dict]:
    teams = await prisma.team.find_many(
        where={"userId": str(user_id), "isActive": True},
        order={"updatedAt": "desc"},
    )
    return [team.model_dump() for team in teams]


async def get_teams_by_board(board_id: uuid.UUID, user_id: uuid.UUID) -> List[dict]:
    teams = await prisma.team.find_many(
        where={
            "boardId": str(board_id),
            "userId": str(user_id),
            "isActive": True,
        },
        order={"updatedAt": "desc"},
    )
    return [team.model_dump() for team in teams]


async def get_team_by_id(team_id: uuid.UUID, user_id: uuid.UUID) -> Optional[dict]:
    team = await prisma.team.find_unique(where={"id": str(team_id)})
    if team and team.userId == str(user_id):
        return team.model_dump()
    return None


async def create_team(
    user_id: uuid.UUID,
    data: TeamCreate,
) -> dict:
    team = await prisma.team.create(
        data={
            "userId": str(user_id),
            "boardId": str(data.board_id) if data.board_id else None,
            "name": data.name,
            "description": data.description,
            "members": Json(
                data.members.model_dump(exclude_none=True) if data.members else {}
            ),
            "orchestrator": Json(
                data.orchestrator.model_dump(exclude_none=True)
                if data.orchestrator
                else {}
            ),
        }
    )
    return team.model_dump()


async def update_team(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    data: TeamUpdate,
) -> Optional[dict]:
    existing = await get_team_by_id(team_id, user_id)
    if not existing:
        return None

    update_data: dict = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.description is not None:
        update_data["description"] = data.description
    if data.members is not None:
        update_data["members"] = Json(data.members.model_dump(exclude_none=True))
    if data.orchestrator is not None:
        update_data["orchestrator"] = Json(
            data.orchestrator.model_dump(exclude_none=True)
        )

    updated = await prisma.team.update(
        where={"id": str(team_id)},
        data=update_data,
    )
    return updated.model_dump()


async def delete_team(team_id: uuid.UUID) -> None:
    await prisma.team.update(
        where={"id": str(team_id)},
        data={"isActive": False},
    )
