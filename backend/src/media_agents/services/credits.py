from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Literal

from fastapi import HTTPException

from media_agents.env import DEMO_MODE, SELF_HOSTED
from media_agents.prisma import prisma
from media_agents.services.user import _to_dict

CommandType = Literal[
    "image",
    "video",
    "music",
    "3d",
    "remesh",
    "retexture",
    "research",
    "agent",
    "chat",
    "help",
]

CREDIT_COSTS: dict[str, int] = {
    "image": 1,
    "research": 2,
    "agent": 2,
    "music": 3,
    "video": 5,
    "remesh": 8,
    "retexture": 8,
    "3d": 10,
    "chat": 1,
    "help": 0,
}

# Maps a specialist capability (used by team coordinator delegations) to the
# CommandType whose CREDIT_COSTS entry should be charged. Add new specialists
# here so per-delegation billing stays accurate.
CAPABILITY_TO_COMMAND: dict[str, CommandType] = {
    # Image
    "text_to_image": "image",
    "image_to_image": "image",
    # Video
    "text_to_video": "video",
    "image_to_video": "video",
    "video_to_video": "video",
    "audio_to_video": "video",
    "human_motion": "video",
    # Audio / music
    "music_generation": "music",
    "text_to_speech": "music",
    "speech_to_speech": "music",
    "audio_to_audio": "music",
    "video_to_audio": "music",
    "speech_to_text": "research",
    # 3D
    "text_to_3d": "3d",
    "image_to_3d": "3d",
    "remesh_3d": "remesh",
    "retexture_3d": "retexture",
    # Vision / analysis
    "vision": "research",
    "video_analysis": "research",
    "structured_output": "chat",
    # Training is the most expensive; bucket as 3d (10 credits) until we add
    # a dedicated tier.
    "training": "3d",
}


def command_for_capability(capability: str) -> CommandType:
    """Return the CommandType whose CREDIT_COSTS entry should be charged for this capability."""
    return CAPABILITY_TO_COMMAND.get(capability, "chat")


def cost_for_capability(capability: str) -> int:
    cmd = command_for_capability(capability)
    return CREDIT_COSTS.get(cmd, 1)


TIER_CREDITS: dict[str, int] = {
    "FREE_TRIAL": 0,
    "STARTER": 30,
    "PLUS": 100,
    "PRO": 250,
    "ENTERPRISE": 0,
}


def get_command_type(message: str) -> CommandType:
    msg = message.lower().strip()
    if msg.startswith("/image") and (len(msg) == 6 or msg[6] == " "):
        return "image"
    if msg.startswith("/video") and (len(msg) == 6 or msg[6] == " "):
        return "video"
    if msg.startswith("/motion"):
        return "video"
    if msg.startswith("/music") and (len(msg) == 6 or msg[6] == " "):
        return "music"
    if msg.startswith("/3d") and (len(msg) == 3 or msg[3] == " "):
        return "3d"
    if msg.startswith("/image-to-3d"):
        return "3d"
    if msg.startswith("/remesh"):
        return "remesh"
    if msg.startswith("/retexture"):
        return "retexture"
    if msg.startswith("/research"):
        return "research"
    if msg.startswith("/create_agent"):
        return "agent"
    if msg.startswith("/help"):
        return "help"
    return "chat"


def check_credits(user: dict, command_type: CommandType) -> None:
    if DEMO_MODE or SELF_HOSTED:
        return
    cost = CREDIT_COSTS.get(command_type, 1)
    if cost == 0:
        return
    total = (user.get("subscriptionCredits") or 0) + (user.get("packCredits") or 0)
    if total < cost:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "insufficient_credits",
                "required": cost,
                "available": total,
            },
        )


async def deduct_credits(user_id: uuid.UUID, command_type: CommandType) -> None:
    if DEMO_MODE or SELF_HOSTED:
        return
    cost = CREDIT_COSTS.get(command_type, 1)
    if cost == 0:
        return
    user = await prisma.user.find_unique(where={"id": str(user_id)})
    if user is None:
        return
    sub = user.subscriptionCredits or 0
    pack = user.packCredits or 0
    from_sub = min(cost, sub)
    from_pack = cost - from_sub
    await prisma.user.update(
        where={"id": str(user_id)},
        data={
            "subscriptionCredits": sub - from_sub,
            "packCredits": pack - from_pack,
        },
    )


async def reset_subscription_credits(
    user_id: uuid.UUID, known_tier: str | None = None
) -> dict | None:
    tier = known_tier
    if not tier:
        user = await prisma.user.find_unique(where={"id": str(user_id)})
        if user is None:
            return None
        tier = (
            user.subscriptionTier.value
            if hasattr(user.subscriptionTier, "value")
            else str(user.subscriptionTier)
        )
    monthly = TIER_CREDITS.get(tier, 0)
    next_reset = datetime.now(timezone.utc) + timedelta(days=30)
    user_updated = await prisma.user.update(
        where={"id": str(user_id)},
        data={"subscriptionCredits": monthly, "creditsResetAt": next_reset},
    )
    return _to_dict(user_updated) if user_updated else {}


async def add_pack_credits(user_id: uuid.UUID, amount: int) -> dict | None:
    user_updated = await prisma.user.update(
        where={"id": str(user_id)},
        data={"packCredits": {"increment": amount}},
    )
    return _to_dict(user_updated) if user_updated else {}
