# src/media_agents/agents/specialist/video_to_video.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Lipsync Video",
    description=(
        "Sync the lips in a video to a new audio track — "
        "dubbing, voiceover replacement, character dialogue"
    ),
    system_prompt=(
        "You are a video-to-video lipsync specialist powered by LatentSync. "
        "Take a video URL and an audio URL; return a video whose lip movements "
        "match the new audio. Works on any face-visible clip. "
        "Default model: fal-ai/latentsync ($0.005/second of output). "
        "Higher-accuracy alternative: fal-ai/sync-lipsync/v2 ($3/minute, "
        "better mouth fidelity). Pixverse and HeyGen variants exist for "
        "fast/avatar-focused work."
    ),
    capabilities=["video_to_video"],
    default_config={
        "capability": "video_to_video",
        "model": "fal-ai/latentsync",
    },
)

video_to_video_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@video_to_video_agent.tool
async def lipsync_video(
    ctx: RunContext[OrchestratorDeps],
    video_url: str,
    audio_url: str,
) -> str:
    """Lipsync a video to a new audio track. Returns the output video URL."""
    model = ctx.deps.model or "fal-ai/latentsync"
    url = await fal_client.lipsync_video(video_url, audio_url, model=model)
    ctx.deps.asset_urls.append(url)
    return f"Lipsynced video at {url}"
