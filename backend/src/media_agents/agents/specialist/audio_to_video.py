# src/media_agents/agents/specialist/audio_to_video.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Talking Avatar",
    description=(
        "Generate a talking-avatar video from a reference image and audio — "
        "lip-synced, natural facial motion"
    ),
    system_prompt=(
        "You are a talking-avatar specialist powered by Stable Avatar. "
        "Take a reference image URL, an audio URL, and a prompt describing the "
        "character's demeanor; return a video of the character speaking. "
        "Prompt example: 'a confident news anchor delivering the report with "
        "subtle hand gestures'. "
        "Default model: fal-ai/stable-avatar ($0.10/generation, up to 5 minutes). "
        "Alternatives: fal-ai/echomimic-v3 ($0.20), fal-ai/longcat-single-avatar "
        "($0.3, very realistic)."
    ),
    capabilities=["audio_to_video"],
    default_config={
        "capability": "audio_to_video",
        "model": "fal-ai/stable-avatar",
    },
)

audio_to_video_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@audio_to_video_agent.tool
async def generate_avatar_video(
    ctx: RunContext[OrchestratorDeps],
    image_url: str,
    audio_url: str,
    prompt: str,
) -> str:
    """Generate a talking-avatar video. Returns the video URL."""
    model = ctx.deps.model or "fal-ai/stable-avatar"
    url = await fal_client.generate_avatar_video(
        image_url, audio_url, prompt, model=model
    )
    ctx.deps.asset_urls.append(url)
    return f"Generated avatar video at {url}"
