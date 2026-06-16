# src/media_agents/agents/specialist/speech_to_speech.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Voice Converter",
    description=(
        "Convert audio from one voice to another — "
        "optional reference voice sample for style matching"
    ),
    system_prompt=(
        "You are a voice-conversion specialist powered by Chatterbox. "
        "Take a source audio URL (the speech to convert) and, optionally, "
        "a target_voice_audio_url (reference voice to match). "
        "If no reference is provided, the default Chatterbox voice is used. "
        "Default model: fal-ai/chatterbox/speech-to-speech (pricing on the "
        "model page). Higher-quality: resemble-ai/chatterboxhd/speech-to-speech."
    ),
    capabilities=["speech_to_speech"],
    default_config={
        "capability": "speech_to_speech",
        "model": "fal-ai/chatterbox/speech-to-speech",
    },
)

speech_to_speech_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@speech_to_speech_agent.tool
async def convert_voice(
    ctx: RunContext[OrchestratorDeps],
    source_audio_url: str,
    target_voice_audio_url: str = "",
) -> str:
    """Convert the voice in a source clip, optionally matching a reference."""
    model = ctx.deps.model or "fal-ai/chatterbox/speech-to-speech"
    reference = target_voice_audio_url or None
    url = await fal_client.convert_voice(
        source_audio_url, target_voice_audio_url=reference, model=model
    )
    ctx.deps.asset_urls.append(url)
    return f"Voice-converted audio at {url}"
