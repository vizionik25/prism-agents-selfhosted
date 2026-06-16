# src/media_agents/agents/specialist/image_to_video.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Image to Video",
    description=(
        "Animate a still image with a motion prompt — "
        "great for product demos, storyboards, character motion"
    ),
    system_prompt=(
        "You are an image-to-video specialist powered by Kling 1.6. "
        "Take a still image URL and a motion prompt; return an animated clip. "
        "Prompt format: describe camera movement + subject motion + mood. "
        "Example: 'slow zoom in, leaves rustling in the wind, golden-hour glow'. "
        "Duration: '5' or '10' seconds. "
        "Default model: fal-ai/kling-video/v1.6/standard/image-to-video. "
        "Video gen blocks 30s-2min; warn the user. Alternatives in same family: "
        "fal-ai/kling-video/v2.6/standard/image-to-video (newer)."
    ),
    capabilities=["image_to_video"],
    default_config={
        "capability": "image_to_video",
        "model": "fal-ai/kling-video/v1.6/standard/image-to-video",
    },
)

image_to_video_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@image_to_video_agent.tool
async def animate_image(
    ctx: RunContext[OrchestratorDeps],
    prompt: str,
    image_url: str,
) -> str:
    """Animate a still image. Returns the video URL."""
    model = ctx.deps.model or "fal-ai/kling-video/v1.6/standard/image-to-video"
    url = await fal_client.generate_video_from_image(prompt, image_url, model=model)
    ctx.deps.asset_urls.append(url)
    return f"Animated image into video at {url}"
