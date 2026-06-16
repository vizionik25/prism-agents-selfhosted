"""Tests for create_agent_from_description.

Covers the happy path (LLM produces a valid AgentTemplate) and the graceful
fallback (LLM keeps producing invalid output → wrap user description as a
plain custom agent).
"""

from __future__ import annotations

import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.test import TestModel

from media_agents.agents import agent_maker
from media_agents.agents.agent_maker import create_agent_from_description
from media_agents.agents.templates import AgentTemplate


async def test_happy_path_returns_validated_template() -> None:
    """When the LLM returns valid structured output, we get an AgentTemplate."""
    valid_args = {
        "name": "Sales Copy Pro",
        "description": "Writes punchy sales copy",
        "system_prompt": "You are a B2B sales copy specialist...",
        "capabilities": ["copywriting"],
        "default_config": {},
    }
    with agent_maker._agent_maker.override(
        model=TestModel(custom_output_args=valid_args)
    ):
        result = await create_agent_from_description("punchy B2B sales copy")

    assert isinstance(result, AgentTemplate)
    assert result.name == "Sales Copy Pro"
    assert "copywriting" in result.capabilities


async def test_fallback_when_model_misbehaves(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the agent run raises UnexpectedModelBehavior, we get the fallback template."""

    async def fake_run(*args, **kwargs):
        raise UnexpectedModelBehavior("model returned garbage")

    monkeypatch.setattr(agent_maker._agent_maker, "run", fake_run)

    description = "an agent that writes haikus"
    result = await create_agent_from_description(description)

    assert isinstance(result, AgentTemplate)
    assert result.name == "Custom Agent"
    # Fallback uses the user's raw description as the system prompt.
    assert result.system_prompt == description
    assert result.capabilities == ["general"]
