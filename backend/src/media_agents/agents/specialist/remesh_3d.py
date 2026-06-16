# src/media_agents/agents/specialist/remesh_3d.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="3D Remesh",
    description=(
        "Optimize topology and polygon count of existing 3D models — "
        "export to GLB, OBJ, FBX, USDZ"
    ),
    system_prompt=(
        "You are a 3D remesh specialist powered by Meshy-5 Remesh. "
        "Remesh 3D models to optimize topology and polygon count. "
        "Requires an existing 3D model URL (GLB, OBJ, FBX, or USDZ). "
        "target_count guidance: game assets 5k-20k, film/VFX 100k-500k, "
        "real-time preview 1k-10k. "
        "Cost: $0.20 per generation. Ask for intended use case before calling the tool."
    ),
    capabilities=["remesh_3d"],
    default_config={"capability": "remesh_3d", "model": "fal-ai/meshy/v5/remesh"},
)

remesh_3d_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@remesh_3d_agent.tool
async def remesh_model(
    ctx: RunContext[OrchestratorDeps],
    model_url: str,
    target_count: int = 50000,
) -> str:
    """Remesh a 3D model to a target polygon count. Returns the remeshed model URL."""
    model = ctx.deps.model or "fal-ai/meshy/v5/remesh"
    url = await fal_client.remesh_3d_model(model_url, target_count, model=model)
    ctx.deps.asset_urls.append(url)
    return f"Remeshed model at {url}"
