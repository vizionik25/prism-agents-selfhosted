# src/media_agents/agents/specialist/vision.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Vision Analyst",
    description=(
        "Analyze images using Claude, GPT-4o, or Llama — "
        "captioning, OCR, visual Q&A, scene description"
    ),
    system_prompt=(
        "You are a visual analysis specialist powered by OpenRouter vision models. "
        "Analyze images to answer questions, caption, OCR, or describe scenes. "
        "Default model: anthropic/claude-sonnet-4.6. "
        "For fast processing: openai/gpt-4o. "
        "Always call analyze_image with the full list of image URLs provided."
    ),
    capabilities=["vision"],
    default_config={"capability": "vision", "model": "anthropic/claude-sonnet-4.6"},
)

vision_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@vision_agent.tool
async def analyze_image(
    ctx: RunContext[OrchestratorDeps],
    image_urls: list[str],
    prompt: str,
) -> str:
    """Analyze one or more images and return the model response."""
    model = ctx.deps.model or "anthropic/claude-sonnet-4.6"
    return await fal_client.analyze_image(image_urls, prompt, model)
