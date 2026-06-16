# src/media_agents/agents/specialist/retexture_3d.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="3D Retexture",
    description=(
        "Apply new AI-generated textures to existing 3D models using text prompts — "
        "PBR material support"
    ),
    system_prompt=(
        "You are a 3D retexture specialist powered by Meshy-5 Retexture. "
        "Apply new textures to existing 3D models using text descriptions. "
        "Requires an existing 3D model URL (GLB, OBJ, FBX, or USDZ). "
        "object_prompt: describe the object ('a wooden treasure chest'). "
        "style_prompt: describe the surface material ('weathered bronze', 'neon cyberpunk metal'). "
        "Cost: $0.30 per generation."
    ),
    capabilities=["retexture_3d"],
    default_config={"capability": "retexture_3d", "model": "fal-ai/meshy/v5/retexture"},
)

retexture_3d_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@retexture_3d_agent.tool
async def retexture_model(
    ctx: RunContext[OrchestratorDeps],
    model_url: str,
    object_prompt: str,
    style_prompt: str = "",
) -> str:
    """Apply new textures to a 3D model. Returns the retextured model URL."""
    model = ctx.deps.model or "fal-ai/meshy/v5/retexture"
    url = await fal_client.retexture_3d_model(
        model_url, object_prompt, style_prompt, model=model
    )
    ctx.deps.asset_urls.append(url)
    return f"Retextured model at {url}"
