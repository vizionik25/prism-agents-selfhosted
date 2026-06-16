# src/media_agents/agents/specialist/text_to_image.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Text to Image",
    description=(
        "Generate images from prompts — "
        "pick a model from the FLUX / Ideogram / SD family"
    ),
    system_prompt=(
        "You are a text-to-image specialist. Craft detailed prompts covering "
        "subject, composition, lighting, style, mood, and color palette. "
        "Default model: fal-ai/flux/schnell (~$0.003/MP — fast, 4-step). "
        "Higher quality: fal-ai/flux/dev (~$0.025/MP) or fal-ai/flux-pro/v1.1 "
        "for maximum fidelity. Best prompt adherence: fal-ai/ideogram/v3. "
        "Always mention the cost you expect before spending on pro variants."
    ),
    capabilities=["text_to_image"],
    default_config={
        "capability": "text_to_image",
        "model": "fal-ai/flux/schnell",
    },
)

text_to_image_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@text_to_image_agent.tool
async def generate_image(
    ctx: RunContext[OrchestratorDeps],
    prompt: str,
) -> str:
    """Generate an image from a text prompt. Returns the image URL."""
    model = ctx.deps.model or "fal-ai/flux/schnell"
    url = await fal_client.generate_image(prompt, model=model)
    ctx.deps.asset_urls.append(url)
    return f"Generated image at {url}"
