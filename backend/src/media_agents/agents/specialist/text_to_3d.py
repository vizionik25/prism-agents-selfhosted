# src/media_agents/agents/specialist/text_to_3d.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Text to 3D",
    description=(
        "Generate fully-textured 3D models from text — "
        "GLB/OBJ ready for Unity, Unreal, and Blender"
    ),
    system_prompt=(
        "You are a text-to-3D specialist powered by Hunyuan3d V3. "
        "Generate production-ready 3D models from text descriptions. "
        "Write detailed prompts: material, shape, surface detail, style. "
        "Example: 'A rustic wooden treasure chest with metal bands and ornate iron lock'. "
        "generate_type options: Normal (default, $0.375), LowPoly (games, $0.45), "
        "Geometry (white model, $0.225). "
        "enable_pbr=True adds physically-based rendering (+$0.15). "
        "Both GLB URL and thumbnail URL are delivered to the user."
    ),
    capabilities=["text_to_3d"],
    default_config={
        "capability": "text_to_3d",
        "model": "fal-ai/hunyuan3d-v3/text-to-3d",
    },
)

text_to_3d_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@text_to_3d_agent.tool
async def generate_3d_model(
    ctx: RunContext[OrchestratorDeps],
    prompt: str,
    generate_type: str = "Normal",
    enable_pbr: bool = False,
) -> str:
    """Generate a 3D model from a text prompt. Returns GLB and thumbnail URLs."""
    model = ctx.deps.model or "fal-ai/hunyuan3d-v3/text-to-3d"
    urls = await fal_client.generate_3d_from_text(
        prompt, generate_type, enable_pbr, model=model
    )
    if urls["glb_url"]:
        ctx.deps.asset_urls.append(urls["glb_url"])
    if urls["thumbnail_url"]:
        ctx.deps.asset_urls.append(urls["thumbnail_url"])
    return (
        f"Generated 3D model at {urls['glb_url']} (thumbnail: {urls['thumbnail_url']})"
    )
