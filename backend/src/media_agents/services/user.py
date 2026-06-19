import uuid
from typing import Optional

from media_agents.prisma import prisma


def _to_dict(user) -> Optional[dict]:
    if user is None:
        return None
    return user.model_dump()


async def get_user_by_id(user_id: uuid.UUID) -> Optional[dict]:
    return _to_dict(await prisma.user.find_unique(where={"id": str(user_id)}))


async def get_user_by_github_id(github_id: str) -> Optional[dict]:
    return _to_dict(await prisma.user.find_unique(where={"githubId": github_id}))


async def create_user(
    github_id: str,
    username: str,
    email: str,
    avatar_url: Optional[str] = None,
    access_token: Optional[str] = None,
) -> dict:
    return _to_dict(
        await prisma.user.create(
            data={
                "githubId": github_id,
                "username": username,
                "email": email,
                "avatarUrl": avatar_url,
                "accessToken": access_token,
            }
        )
    )


async def update_user(
    user_id: uuid.UUID,
    username: Optional[str] = None,
    avatar_url: Optional[str] = None,
    access_token: Optional[str] = None,
) -> dict:
    return _to_dict(
        await prisma.user.update(
            where={"id": str(user_id)},
            data={
                "username": username,
                "avatarUrl": avatar_url,
                "accessToken": access_token,
            },
        )
    )


async def update_user_billing(
    user_id: uuid.UUID,
    stripe_customer_id=None,
    stripe_subscription_id=None,
    subscription_tier=None,
    subscription_credits=None,
    pack_credits_delta=None,
) -> dict:
    data = {}
    if stripe_customer_id is not None:
        data["stripeCustomerId"] = stripe_customer_id
    if stripe_subscription_id is not None:
        data["stripeSubscriptionId"] = stripe_subscription_id
    if subscription_tier is not None:
        data["subscriptionTier"] = subscription_tier
    if subscription_credits is not None:
        data["subscriptionCredits"] = subscription_credits
    if pack_credits_delta is not None:
        data["packCredits"] = {"increment": pack_credits_delta}
    user = await prisma.user.update(where={"id": str(user_id)}, data=data)
    return _to_dict(user) if user else {}


async def get_user_by_email(email: str) -> Optional[dict]:
    return _to_dict(await prisma.user.find_unique(where={"email": email}))


async def create_local_user(
    username: str,
    email: str,
    password_hash: str,
) -> dict:
    return _to_dict(
        await prisma.user.create(
            data={
                "username": username,
                "email": email,
                "passwordHash": password_hash,
            }
        )
    )


async def get_user_by_username(username: str) -> Optional[dict]:
    return _to_dict(await prisma.user.find_unique(where={"username": username}))
