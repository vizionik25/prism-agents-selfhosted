"""
Daily reconciliation job — syncs user traits to PostHog.

Use this to catch drift between the users table and analytics traits if a
live event failed to send. Schedule via cron (or your platform's scheduler).

Run:
    uv run python -m scripts.sync_analytics_traits

The script exits non-zero on any failure, so a scheduler can alert on it.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from media_agents.analytics import analytics
from media_agents.analytics.traits import full_identify_payload
from media_agents.prisma import prisma

import os

logger = logging.getLogger(__name__)


def process_user(user_dict: dict) -> None:
    payload = full_identify_payload(user_dict)
    analytics.identify(
        user_id=user_dict["id"],
        traits=payload,
        email=payload.get("email"),
    )


async def sync_all() -> int:
    await prisma.connect()
    try:
        synced = 0
        cursor = None
        batch_size = int(os.environ.get("SYNC_BATCH_SIZE", "1000"))

        while True:
            # Build query options for cursor-based pagination
            query_opts = {"take": batch_size, "order": {"id": "asc"}}
            if cursor:
                query_opts["cursor"] = {"id": cursor}
                query_opts["skip"] = 1

            users = await prisma.user.find_many(**query_opts)

            if not users:
                break

            await asyncio.gather(
                *(asyncio.to_thread(process_user, user.model_dump()) for user in users)
            )
            synced += len(users)

            # Update cursor for the next iteration
            cursor = users[-1].id

            # If we fetched fewer than batch_size, we've reached the end
            if len(users) < batch_size:
                break

        logger.info("Synced traits for %d users to PostHog.", synced)
        return synced
    finally:
        analytics.shutdown()
        await prisma.disconnect()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(sync_all())
    except Exception:  # noqa: BLE001
        logger.exception("sync_analytics_traits failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
