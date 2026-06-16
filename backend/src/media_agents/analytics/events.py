"""Event name constants. Matches .telemetry/tracking-plan.yaml v1."""

from __future__ import annotations
from typing import Final

# Lifecycle
USER_SIGNED_UP: Final[str] = "user.signed_up"
USER_SIGNED_IN: Final[str] = "user.signed_in"
USER_SIGNED_OUT: Final[str] = "user.signed_out"

# Core value
GENERATION_STARTED: Final[str] = "generation.started"
GENERATION_COMPLETED: Final[str] = "generation.completed"
BOARD_CREATED: Final[str] = "board.created"
BOARD_DELETED: Final[str] = "board.deleted"
AGENT_CREATED: Final[str] = "agent.created"
AGENT_DELETED: Final[str] = "agent.deleted"
TEAM_CREATED: Final[str] = "team.created"
TEAM_DELETED: Final[str] = "team.deleted"

# Billing
UPGRADE_MODAL_VIEWED: Final[str] = "upgrade_modal.viewed"
CHECKOUT_STARTED: Final[str] = "checkout.started"
SUBSCRIPTION_CHANGED: Final[str] = "subscription.changed"
PACK_PURCHASED: Final[str] = "pack.purchased"
CREDITS_DEPLETED: Final[str] = "credits.depleted"
