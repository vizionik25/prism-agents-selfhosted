from fastapi import APIRouter, Depends, HTTPException, status
import uuid
from datetime import datetime
from typing import Optional

from media_agents.auth.dependencies import get_current_user
from media_agents.env import DEMO_MODE
from media_agents.services import board as board_service
from media_agents.services import generation as generation_service
from media_agents.analytics import analytics
from media_agents.analytics.events import BOARD_CREATED, BOARD_DELETED
from pydantic import BaseModel

router = APIRouter(prefix="/boards", tags=["boards"])


async def _ensure_demo_user(user_id: str) -> None:
    """Create the demo user row if it doesn't exist yet (DEMO_MODE only)."""
    from media_agents.prisma import prisma

    existing = await prisma.user.find_unique(where={"id": user_id})
    if existing is None:
        try:
            await prisma.user.create(
                data={
                    "id": user_id,
                    "githubId": "demo",
                    "username": "Demo User",
                    "email": "demo@prismagents.com",
                    "subscriptionTier": "PRO",
                    "subscriptionCredits": 999999,
                    "packCredits": 999999,
                },
            )
        except Exception:
            pass  # already exists (race condition)


class BoardCreate(BaseModel):
    name: str
    description: Optional[str] = None


class BoardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class BoardResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str


class BoardListResponse(BaseModel):
    boards: list[BoardResponse]


def _format_datetime(dt: datetime) -> str:
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


@router.get("", response_model=BoardListResponse)
async def list_boards(current_user: dict = Depends(get_current_user)):
    if DEMO_MODE:
        await _ensure_demo_user(current_user["id"])
    boards = await board_service.get_boards_by_user(uuid.UUID(current_user["id"]))
    return BoardListResponse(
        boards=[
            BoardResponse(
                id=b["id"],
                name=b["name"],
                description=b.get("description"),
                created_at=_format_datetime(b["createdAt"]),
                updated_at=_format_datetime(b["updatedAt"]),
            )
            for b in boards
        ]
    )


@router.post("", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
async def create_board(
    data: BoardCreate,
    current_user: dict = Depends(get_current_user),
):
    if DEMO_MODE:
        await _ensure_demo_user(current_user["id"])
    board = await board_service.create_board(
        uuid.UUID(current_user["id"]), data.name, data.description
    )
    analytics.capture(
        user_id=current_user["id"],
        event=BOARD_CREATED,
        email=current_user.get("email"),
        properties={
            "board_id": board["id"],
            "has_description": bool(data.description),
        },
    )
    return BoardResponse(
        id=board["id"],
        name=board["name"],
        description=board.get("description"),
        created_at=_format_datetime(board["createdAt"]),
        updated_at=_format_datetime(board["updatedAt"]),
    )


@router.get("/{board_id}", response_model=BoardResponse)
async def get_board(
    board_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    board = await board_service.get_board_by_id(board_id, uuid.UUID(current_user["id"]))
    if board is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Board not found"
        )
    return BoardResponse(
        id=board["id"],
        name=board["name"],
        description=board.get("description"),
        created_at=_format_datetime(board["createdAt"]),
        updated_at=_format_datetime(board["updatedAt"]),
    )


@router.put("/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: uuid.UUID,
    data: BoardUpdate,
    current_user: dict = Depends(get_current_user),
):
    board = await board_service.get_board_by_id(board_id, uuid.UUID(current_user["id"]))
    if board is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Board not found"
        )
    updated = await board_service.update_board(
        board_id, uuid.UUID(current_user["id"]), data.name, data.description
    )
    return BoardResponse(
        id=updated["id"],
        name=updated["name"],
        description=updated.get("description"),
        created_at=_format_datetime(updated["createdAt"]),
        updated_at=_format_datetime(updated["updatedAt"]),
    )


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(
    board_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    board = await board_service.get_board_by_id(board_id, uuid.UUID(current_user["id"]))
    if board is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Board not found"
        )
    generations = await generation_service.get_generations_by_board(
        board_id, uuid.UUID(current_user["id"])
    )
    created = board.get("createdAt")
    age_days = 0
    if hasattr(created, "date"):
        age_days = max(0, (datetime.now(created.tzinfo).date() - created.date()).days)
    await board_service.delete_board(board_id)
    analytics.capture(
        user_id=current_user["id"],
        event=BOARD_DELETED,
        email=current_user.get("email"),
        properties={
            "board_id": str(board_id),
            "age_days": age_days,
            "generations_count": len(generations),
        },
    )
