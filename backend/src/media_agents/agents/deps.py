"""Shared dependency types for PydanticAI agents.

Kept in a separate module so specialist agents can import OrchestratorDeps
without creating a circular import with orchestrator.py.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrchestratorDeps:
    user_id: uuid.UUID
    board_id: uuid.UUID
    system_prompt: str
    asset_urls: list[str] = field(default_factory=list)
    model: str | None = None
    # Per-team-run credit tracking. Populated by the team coordinator path;
    # untouched by single-agent and slash-command paths (which use the existing
    # one-shot deduction in routers/chat.py).
    spent_credits: int = 0
    max_credits: int | None = None
    attachments: list[dict[str, Any]] = field(default_factory=list)
