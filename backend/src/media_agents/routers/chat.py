import logging
import uuid

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from media_agents.auth.dependencies import get_current_user
from media_agents.env import DEMO_MODE
from media_agents.services import board as board_service
from media_agents.services.chat import (
    ChatRequest,
    stream_chat_events,
    validate_attachments,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


async def _ensure_demo_user_in_db(user_id: uuid.UUID) -> None:
    """In DEMO_MODE, ensure the demo user row exists in the database."""
    from media_agents.prisma import prisma as _prisma

    existing = await _prisma.user.find_unique(where={"id": str(user_id)})
    if existing is None:
        try:
            await _prisma.user.create(
                data={
                    "id": str(user_id),
                    "githubId": "demo",
                    "username": "Demo User",
                    "email": "demo@prismagents.com",
                    "subscriptionTier": "PRO",
                    "subscriptionCredits": 999999,
                    "packCredits": 999999,
                },
            )
        except Exception:
            pass  # race condition or already exists


async def _ensure_demo_board(user_id: uuid.UUID, board_id: uuid.UUID) -> None:
    """In DEMO_MODE, ensure the requested board exists for the demo user."""
    board = await board_service.get_board_by_id(board_id, user_id)
    if board is None:
        try:
            from media_agents.prisma import prisma as _prisma

            await _prisma.board.create(
                data={
                    "id": str(board_id),
                    "userId": str(user_id),
                    "name": "Demo Board",
                    "description": "Auto-created for demo mode",
                },
            )
        except Exception:
            pass  # race condition or already exists


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = uuid.UUID(current_user["id"])
    attachments_list = getattr(request, "attachments", None)
    if attachments_list:
        validate_attachments(attachments_list)
    if DEMO_MODE:
        await _ensure_demo_user_in_db(user_id)
        await _ensure_demo_board(user_id, request.board_id)
    return EventSourceResponse(stream_chat_events(request, user_id))
