# src/media_agents/agents/specialist/image_to_3d.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client, ImageTo3DRequest
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Image to 3D",
    description=(
        "Convert photos of an object into a 3D model — "
        "front view required, side/back views improve quality"
    ),
    system_prompt=(
        "You are an image-to-3D specialist powered by Meshy-5 Multi. "
        "Reconstruct production-ready 3D models from photographs. "
        "A front-view image URL is required. "
        "Back/left/right views are optional but improve accuracy. "
        "Best results: clean background, consistent lighting, no motion blur. "
        "Cost: $0.40 per generation. Both model GLB URL and thumbnail are delivered."
    ),
    capabilities=["image_to_3d"],
    default_config={
        "capability": "image_to_3d",
        "model": "fal-ai/meshy/v5/multi-image-to-3d",
    },
)

image_to_3d_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@image_to_3d_agent.tool
async def generate_3d_from_images(
    ctx: RunContext[OrchestratorDeps],
    image_url: str,
    left_image_url: str = "",
    back_image_url: str = "",
    right_image_url: str = "",
) -> str:
    """Generate a 3D model from images. Returns model URL and thumbnail URL."""
    model = ctx.deps.model or "fal-ai/meshy/v5/multi-image-to-3d"
    request = ImageTo3DRequest(
        image_url=image_url,
        left_image_url=left_image_url,
        back_image_url=back_image_url,
        right_image_url=right_image_url,
    )
    urls = await fal_client.generate_3d_from_images(request, model=model)
    if urls["model_url"]:
        ctx.deps.asset_urls.append(urls["model_url"])
    if urls["thumbnail_url"]:
        ctx.deps.asset_urls.append(urls["thumbnail_url"])
    return f"Generated 3D model at {urls['model_url']} (thumbnail: {urls['thumbnail_url']})"
