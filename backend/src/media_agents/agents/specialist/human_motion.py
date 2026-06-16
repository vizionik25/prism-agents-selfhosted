# src/media_agents/agents/specialist/human_motion.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Human Motion Generator",
    description=(
        "Generate 3D human motion animations from text — "
        "walking, dancing, sports, any body movement"
    ),
    system_prompt=(
        "You are a 3D human motion generation specialist powered by Hunyuan Motion. "
        "Generate realistic 3D motion sequences from natural language. "
        "Be specific about motion type, speed, and style. "
        "Example: 'a person doing a slow pirouette', 'someone waving hello enthusiastically'. "
        "For sports, specify the action phase: 'a batter swinging through a baseball'. "
        "Output is a video URL showing the 3D motion sequence."
    ),
    capabilities=["human_motion"],
    default_config={
        "capability": "human_motion",
        "model": "fal-ai/hunyuan-motion/fast",
    },
)

human_motion_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@human_motion_agent.tool
async def generate_human_motion(ctx: RunContext[OrchestratorDeps], prompt: str) -> str:
    """Generate a 3D human motion sequence. Returns the video URL."""
    model = ctx.deps.model or "fal-ai/hunyuan-motion/fast"
    url = await fal_client.generate_human_motion(prompt, model=model)
    ctx.deps.asset_urls.append(url)
    return f"Generated motion sequence at {url}"
