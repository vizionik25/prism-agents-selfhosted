"""Generate a custom AgentTemplate from a free-text user description.

Uses a PydanticAI agent with `output_type=AgentTemplate` so the LLM's response is
structurally validated. Falls back to a hand-built template if the LLM repeatedly
fails to produce a valid one (e.g., returns prose instead of structured output).
"""

from __future__ import annotations

import logging

from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior

from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.templates import AgentTemplate

logger = logging.getLogger(__name__)


_INSTRUCTIONS = """You are an agent creation specialist. Convert the user's
description of an AI agent into a structured AgentTemplate with these fields:

- name: short display name (1-4 words)
- description: one sentence describing the agent's purpose
- system_prompt: the actual system prompt that will be sent to the underlying LLM
  to make the agent behave as described — write it in second person ("You are ...")
  and include any relevant guidelines or constraints
- capabilities: list of short capability tags (e.g. ["image_generation",
  "copywriting"])
- default_config: optional configuration dict; use {} if nothing applies

Templates available for reference: Image Generator, Video Creator, Brand Designer,
Creative Writer, Research Analyst.
"""


_agent_maker: Agent[None, AgentTemplate] = Agent(
    fal_chat_model,
    output_type=AgentTemplate,
    instructions=_INSTRUCTIONS,
    retries=2,
)


async def create_agent_from_description(user_description: str) -> AgentTemplate:
    """Generate an AgentTemplate from a user's plain-text request.

    Returns a graceful-fallback template if the LLM fails to produce a valid one
    after the configured retries — preserving the prior behavior where invalid
    JSON wasn't fatal.
    """
    try:
        result = await _agent_maker.run(
            f"Create a custom agent based on this description:\n{user_description}"
        )
        return result.output
    except UnexpectedModelBehavior:
        logger.warning(
            "agent_maker failed to produce a valid AgentTemplate; using fallback"
        )
        return AgentTemplate(
            name="Custom Agent",
            description="User-created custom agent",
            system_prompt=user_description,
            capabilities=["general"],
            default_config={},
        )
