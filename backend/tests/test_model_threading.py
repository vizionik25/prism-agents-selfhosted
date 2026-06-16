from __future__ import annotations
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.orchestrator import AgentOrchestrator


def test_orchestrator_deps_model_defaults_to_none():
    deps = OrchestratorDeps(
        user_id=uuid.uuid4(),
        board_id=uuid.uuid4(),
        system_prompt="test",
    )
    assert deps.model is None


def test_orchestrator_deps_accepts_model():
    deps = OrchestratorDeps(
        user_id=uuid.uuid4(),
        board_id=uuid.uuid4(),
        system_prompt="test",
        model="anthropic/claude-sonnet-4.6",
    )
    assert deps.model == "anthropic/claude-sonnet-4.6"


@pytest.mark.asyncio
async def test_vision_tool_uses_deps_model():
    deps = OrchestratorDeps(
        user_id=uuid.uuid4(),
        board_id=uuid.uuid4(),
        system_prompt="test",
        model="openai/gpt-4o",
    )
    with patch(
        "media_agents.agents.specialist.vision.fal_client.analyze_image",
        new_callable=AsyncMock,
        return_value="analysis result",
    ) as mock_analyze:
        from media_agents.agents.specialist.vision import analyze_image

        ctx = type("Ctx", (), {"deps": deps})()
        result = await analyze_image(
            ctx, ["https://example.com/img.jpg"], "describe it"
        )
        mock_analyze.assert_called_once_with(
            ["https://example.com/img.jpg"], "describe it", "openai/gpt-4o"
        )
        assert result == "analysis result"


@pytest.mark.asyncio
async def test_vision_tool_falls_back_to_default_model():
    deps = OrchestratorDeps(
        user_id=uuid.uuid4(),
        board_id=uuid.uuid4(),
        system_prompt="test",
        model=None,
    )
    with patch(
        "media_agents.agents.specialist.vision.fal_client.analyze_image",
        new_callable=AsyncMock,
        return_value="result",
    ) as mock_analyze:
        from media_agents.agents.specialist.vision import analyze_image

        ctx = type("Ctx", (), {"deps": deps})()
        await analyze_image(ctx, ["https://example.com/img.jpg"], "describe it")
        mock_analyze.assert_called_once_with(
            ["https://example.com/img.jpg"],
            "describe it",
            "anthropic/claude-sonnet-4.6",
        )


def test_orchestrator_get_model_returns_none_without_custom_agent():
    orch = AgentOrchestrator(uuid.uuid4(), uuid.uuid4())
    assert orch._get_model() is None


def test_orchestrator_get_model_returns_config_model():
    orch = AgentOrchestrator(uuid.uuid4(), uuid.uuid4())
    orch.set_custom_agent(
        system_prompt="You are helpful.",
        config={"capability": "vision", "model": "openai/gpt-4o"},
    )
    assert orch._get_model() == "openai/gpt-4o"


def test_orchestrator_get_model_returns_none_when_model_not_in_config():
    orch = AgentOrchestrator(uuid.uuid4(), uuid.uuid4())
    orch.set_custom_agent(
        system_prompt="You are helpful.",
        config={"capability": "vision"},
    )
    assert orch._get_model() is None
