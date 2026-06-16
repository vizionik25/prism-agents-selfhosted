"""Research helper — wraps the chat LLM with a research-specialist instruction."""

from __future__ import annotations

from typing import Optional

from pydantic_ai import Agent

from media_agents.agents.fal_model import fal_chat_model


_INSTRUCTIONS = """You are a research specialist. Gather context for creative
work and present findings in this format:

1. Key findings summary
2. Relevant context
3. Potential sources / references
4. Suggested next steps

Cite sources when providing factual information. Identify gaps. Suggest further
research directions if needed.
"""

_research_agent: Agent[None, str] = Agent(fal_chat_model, instructions=_INSTRUCTIONS)


async def research_task(query: str, context: Optional[dict] = None) -> str:
    prompt = f"Research query: {query}"
    if context:
        prompt += f"\n\nContext: {context}"
    result = await _research_agent.run(prompt)
    return result.output
