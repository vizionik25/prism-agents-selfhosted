# src/media_agents/agents/specialist/video_to_audio.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Foley / Soundtrack",
    description=(
        "Generate a synced soundtrack or sound-effect track for a silent video"
    ),
    system_prompt=(
        "You are a video-to-audio Foley specialist powered by Kling V2A. "
        "Take a silent (or music-less) video URL and optional prompts: "
        "sound_effect_prompt (e.g. 'footsteps on gravel, distant thunder') and "
        "background_music_prompt (e.g. 'tense cinematic orchestral'). "
        "Both are capped at 200 chars; video must be 3-20s, <100MB. "
        "Default model: fal-ai/kling-video/video-to-audio ($0.035/video). "
        "Cheaper option: mirelo-ai/sfx-v1/video-to-audio ($0.007/second). "
        "Returns BOTH the dubbed video and the raw audio track."
    ),
    capabilities=["video_to_audio"],
    default_config={
        "capability": "video_to_audio",
        "model": "fal-ai/kling-video/video-to-audio",
    },
)

video_to_audio_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@video_to_audio_agent.tool
async def generate_soundtrack(
    ctx: RunContext[OrchestratorDeps],
    video_url: str,
    sound_effect_prompt: str = "",
    background_music_prompt: str = "",
) -> str:
    """Generate a soundtrack for a video. Returns dubbed-video and audio URLs."""
    model = ctx.deps.model or "fal-ai/kling-video/video-to-audio"
    urls = await fal_client.generate_video_soundtrack(
        video_url,
        sound_effect_prompt=sound_effect_prompt,
        background_music_prompt=background_music_prompt,
        model=model,
    )
    if urls["video_url"]:
        ctx.deps.asset_urls.append(urls["video_url"])
    if urls["audio_url"]:
        ctx.deps.asset_urls.append(urls["audio_url"])
    return (
        f"Generated soundtrack — dubbed video: {urls['video_url']}, "
        f"audio track: {urls['audio_url']}"
    )
