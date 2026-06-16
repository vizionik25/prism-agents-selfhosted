# src/media_agents/agents/specialist/text_to_video.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Text to Video",
    description=(
        "Generate short video clips from text — "
        "covers motion, camera work, style, pacing"
    ),
    system_prompt=(
        "You are a text-to-video specialist. Write prompts that cover "
        "motion, camera movement, subject, environment, lighting, and pacing. "
        "Default model: fal-ai/kling-video/v1.6/standard/text-to-video "
        "(balanced quality/cost). Faster and cheaper: "
        "fal-ai/luma-dream-machine/ray-2-flash. Higher quality: "
        "fal-ai/veo3.1 or fal-ai/kling-video/v2 (slower, more expensive). "
        "Video generation blocks for 30s-2min — warn the user."
    ),
    capabilities=["text_to_video"],
    default_config={
        "capability": "text_to_video",
        "model": "fal-ai/kling-video/v1.6/standard/text-to-video",
    },
)

text_to_video_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@text_to_video_agent.tool
async def generate_video(
    ctx: RunContext[OrchestratorDeps],
    prompt: str,
) -> str:
    """Generate a short video from a text prompt. Returns the video URL."""
    model = ctx.deps.model or "fal-ai/kling-video/v1.6/standard/text-to-video"
    url = await fal_client.generate_video(prompt, model=model)
    ctx.deps.asset_urls.append(url)
    return f"Generated video at {url}"
