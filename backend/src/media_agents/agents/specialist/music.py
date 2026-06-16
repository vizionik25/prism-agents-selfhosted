# src/media_agents/agents/specialist/music.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Music Generator",
    description=(
        "Create complete music tracks with vocals and full arrangements "
        "from a style description and optional lyrics"
    ),
    system_prompt=(
        "You are a music generation specialist powered by MiniMax Music 2.6. "
        "Produce fully-arranged music from style descriptions and optional lyrics. "
        "Style prompt format: genre, mood, BPM, key instruments, vocal style (10-2000 chars). "
        "Example: 'City Pop, 80s retro, groovy synth bass, warm female vocal, 104 BPM'. "
        "For vocal songs, ask for or write lyrics using [Intro]/[Verse]/[Chorus]/[Bridge]/[Outro] tags. "
        "Set is_instrumental=True only when user explicitly wants no vocals."
    ),
    capabilities=["music_generation"],
    default_config={
        "capability": "music_generation",
        "model": "fal-ai/minimax-music/v2.6",
    },
)

music_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@music_agent.tool
async def generate_music(
    ctx: RunContext[OrchestratorDeps],
    prompt: str,
    lyrics: str = "",
    is_instrumental: bool = False,
) -> str:
    """Generate a complete music track. Returns the audio URL."""
    model = ctx.deps.model or "fal-ai/minimax-music/v2.6"
    url = await fal_client.generate_music(prompt, lyrics, is_instrumental, model=model)
    ctx.deps.asset_urls.append(url)
    return f"Generated music track at {url}"
