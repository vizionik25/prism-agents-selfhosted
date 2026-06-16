# src/media_agents/agents/specialist/chat_openai.py
from __future__ import annotations
from pydantic_ai import Agent
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="OpenRouter Chat",
    description="Direct access to OpenRouter's OpenAI-compatible chat — any model, full tool-calling support",
    system_prompt=(
        "You are a direct interface to OpenRouter's OpenAI-compatible API via fal.ai. "
        "Respond directly and thoughtfully. Use fenced code blocks for code. "
        "Cite uncertainty clearly — do not fabricate facts."
    ),
    capabilities=["openrouter_chat"],
    default_config={
        "capability": "openrouter_chat",
        "model": "openrouter/router/openai/v1/chat/completions",
    },
)

chat_openai_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)
