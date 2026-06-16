import uuid
from typing import Optional, List

from media_agents.prisma import prisma


async def get_boards_by_user(user_id: uuid.UUID) -> List[dict]:
    boards = await prisma.board.find_many(
        where={"userId": str(user_id)},
        order={"updatedAt": "desc"},
    )
    return [board.model_dump() for board in boards]


async def get_board_by_id(board_id: uuid.UUID, user_id: uuid.UUID) -> Optional[dict]:
    board = await prisma.board.find_unique(
        where={"id": str(board_id)},
        include={"agents": True},
    )
    if board and board.userId == str(user_id):
        return board.model_dump()
    return None


async def create_board(
    user_id: uuid.UUID, name: str, description: Optional[str] = None
) -> dict:
    board = await prisma.board.create(
        data={
            "userId": str(user_id),
            "name": name,
            "description": description,
        }
    )
    return board.model_dump()


async def update_board(
    board_id: uuid.UUID,
    user_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Optional[dict]:
    board = await get_board_by_id(board_id, user_id)
    if not board:
        return None

    update_data: dict = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description

    updated = await prisma.board.update(
        where={"id": str(board_id)},
        data=update_data,
    )
    return updated.model_dump()


async def delete_board(board_id: uuid.UUID) -> None:
    await prisma.board.delete(where={"id": str(board_id)})
