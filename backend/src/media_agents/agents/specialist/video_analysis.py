# src/media_agents/agents/specialist/video_analysis.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Video Analyst",
    description=(
        "Analyze video content using Claude or GPT-4o — "
        "transcription, scene description, summarization, visual Q&A"
    ),
    system_prompt=(
        "You are a video analysis specialist powered by OpenRouter video enterprise models. "
        "Process mp4, mpeg, mov, or webm files for transcription, description, or Q&A. "
        "Default model: anthropic/claude-sonnet-4.6. "
        "Format transcriptions with speaker labels when possible. "
        "YouTube links are supported."
    ),
    capabilities=["video_analysis"],
    default_config={
        "capability": "video_analysis",
        "model": "anthropic/claude-sonnet-4.6",
    },
)

video_analysis_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@video_analysis_agent.tool
async def analyze_video(
    ctx: RunContext[OrchestratorDeps],
    video_urls: list[str],
    prompt: str,
) -> str:
    """Analyze one or more videos and return the model response."""
    model = ctx.deps.model or "anthropic/claude-sonnet-4.6"
    return await fal_client.analyze_video(video_urls, prompt, model)
