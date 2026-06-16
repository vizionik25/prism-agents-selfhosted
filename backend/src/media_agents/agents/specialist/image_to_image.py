# src/media_agents/agents/specialist/image_to_image.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Image Editor",
    description=(
        "Edit existing images with natural language — "
        "swap backgrounds, change subjects, restyle, retouch"
    ),
    system_prompt=(
        "You are an image-editing specialist powered by Nano Banana (Gemini 2.5 Flash Image). "
        "Call edit_image with the image URL(s) and a clear edit instruction. "
        "Example: 'make the sky a dramatic sunset' or 'replace the background with a forest'. "
        "Default model: fal-ai/nano-banana/edit ($0.039/image, best prompt adherence). "
        "Cheaper alternatives: fal-ai/flux-2/flash/edit ($0.005/MP), "
        "fal-ai/gpt-image-1/edit-image ($0.002). "
        "For pure upscaling use fal-ai/esrgan (very cheap)."
    ),
    capabilities=["image_to_image"],
    default_config={
        "capability": "image_to_image",
        "model": "fal-ai/nano-banana/edit",
    },
)

image_to_image_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@image_to_image_agent.tool
async def edit_image(
    ctx: RunContext[OrchestratorDeps],
    prompt: str,
    image_urls: list[str],
) -> str:
    """Edit one or more images with a natural-language instruction."""
    model = ctx.deps.model or "fal-ai/nano-banana/edit"
    url = await fal_client.edit_image(prompt, image_urls, model=model)
    ctx.deps.asset_urls.append(url)
    return f"Edited image at {url}"
