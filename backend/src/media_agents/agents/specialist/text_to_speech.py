# src/media_agents/agents/specialist/text_to_speech.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Text to Speech",
    description=(
        "Convert text into natural-sounding speech — "
        "pick a voice preset and get an audio URL back"
    ),
    system_prompt=(
        "You are a text-to-speech specialist powered by MiniMax Speech-02 Turbo. "
        "Call generate_speech with the text the user wants spoken. "
        "Voice presets include 'Wise_Woman', 'Deep_Voice_Man', 'Friendly_Person', "
        "'Calm_Woman', 'Casual_Guy', 'Lively_Girl'. Ask the user if you are unsure. "
        "Cost: ~$0.06 per generation on the Turbo model; the HD variant "
        "(fal-ai/minimax/speech-02-hd) is $0.10 for higher fidelity. "
        "Max input is 5000 characters — split longer text into chunks."
    ),
    capabilities=["text_to_speech"],
    default_config={
        "capability": "text_to_speech",
        "model": "fal-ai/minimax/speech-02-turbo",
    },
)

text_to_speech_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@text_to_speech_agent.tool
async def generate_speech(
    ctx: RunContext[OrchestratorDeps],
    text: str,
    voice_id: str = "Wise_Woman",
) -> str:
    """Synthesize speech from text. Returns the audio URL."""
    model = ctx.deps.model or "fal-ai/minimax/speech-02-turbo"
    url = await fal_client.generate_speech(text, voice_id=voice_id, model=model)
    ctx.deps.asset_urls.append(url)
    return f"Generated speech at {url}"
