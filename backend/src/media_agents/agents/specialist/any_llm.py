# src/media_agents/agents/specialist/any_llm.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Any LLM",
    description="Route prompts to any of 200+ models (Claude, GPT, Llama, DeepSeek) via OpenRouter",
    system_prompt=(
        "You are an AI model router. Answer user prompts by calling the query_llm tool. "
        "Default model: anthropic/claude-sonnet-4.6. "
        "Supported models: anthropic/claude-sonnet-4.6, "
        "openai/gpt-4o, meta-llama/llama-4-maverick, deepseek/deepseek-r1."
    ),
    capabilities=["any_llm"],
    default_config={"capability": "any_llm", "model": "anthropic/claude-sonnet-4.6"},
)

any_llm_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@any_llm_agent.tool
async def query_llm(
    ctx: RunContext[OrchestratorDeps],
    prompt: str,
    system_prompt: str = "",
) -> str:
    """Send a prompt to the configured LLM via OpenRouter. Returns the model response."""
    model = ctx.deps.model or "anthropic/claude-sonnet-4.6"
    return await fal_client.any_llm_completion(prompt, model, system_prompt)
