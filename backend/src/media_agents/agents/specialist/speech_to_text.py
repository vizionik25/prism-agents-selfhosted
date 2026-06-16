# src/media_agents/agents/specialist/speech_to_text.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Audio Transcription",
    description=(
        "Transcribe or translate audio files to text — "
        "Whisper under the hood, auto language detection"
    ),
    system_prompt=(
        "You are an audio transcription specialist powered by Whisper. "
        "Call transcribe_audio with the audio file URL. "
        "task='transcribe' (same language) or 'translate' (to English). "
        "Leave language=None for auto-detection, or pass an ISO code like 'en', 'es'. "
        "Default model: fal-ai/whisper. Faster alternative: "
        "fal-ai/wizper (fal-optimized Whisper v3). "
        "Premium: fal-ai/elevenlabs/speech-to-text/scribe-v2 ($0.008/input). "
        "Supports mp3, mp4, wav, webm, m4a."
    ),
    capabilities=["speech_to_text"],
    default_config={
        "capability": "speech_to_text",
        "model": "fal-ai/whisper",
    },
)

speech_to_text_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@speech_to_text_agent.tool
async def transcribe_audio(
    ctx: RunContext[OrchestratorDeps],
    audio_url: str,
    task: str = "transcribe",
    language: str | None = None,
) -> str:
    """Transcribe or translate audio. Returns the text."""
    model = ctx.deps.model or "fal-ai/whisper"
    return await fal_client.transcribe_audio(
        audio_url, task=task, language=language, model=model
    )
