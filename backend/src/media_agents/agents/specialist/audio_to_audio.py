# src/media_agents/agents/specialist/audio_to_audio.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Stem Separator",
    description=(
        "Split a song into vocals, drums, bass, and other stems — "
        "Demucs 6-stem model by default"
    ),
    system_prompt=(
        "You are an audio stem-separation specialist powered by Demucs. "
        "Call separate_stems with the audio URL. Default model htdemucs_6s "
        "returns six stems: vocals, drums, bass, guitar, piano, other. "
        "Use htdemucs (default Demucs) for the classic 4-stem split. "
        "Pricing on fal-ai/demucs is not publicly listed; check the model page "
        "before large batches. Alternative: fal-ai/elevenlabs/audio-isolation "
        "for vocal-only isolation."
    ),
    capabilities=["audio_to_audio"],
    default_config={
        "capability": "audio_to_audio",
        "model": "fal-ai/demucs",
    },
)

audio_to_audio_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@audio_to_audio_agent.tool
async def separate_stems(
    ctx: RunContext[OrchestratorDeps],
    audio_url: str,
    output_format: str = "mp3",
) -> str:
    """Separate a song into stems. Returns a summary string; each stem URL is
    pushed into asset_urls for the orchestrator to emit."""
    model = ctx.deps.model or "fal-ai/demucs"
    stems = await fal_client.separate_stems(
        audio_url, output_format=output_format, model=model
    )
    for url in stems.values():
        ctx.deps.asset_urls.append(url)
    listing = ", ".join(f"{k}: {v}" for k, v in stems.items())
    return f"Separated {len(stems)} stems — {listing}"
