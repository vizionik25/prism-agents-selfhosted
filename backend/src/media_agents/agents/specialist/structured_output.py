# src/media_agents/agents/specialist/structured_output.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="Structured Output",
    description=(
        "Extract structured JSON from prompts or images — "
        "describe the schema and point at the source content"
    ),
    system_prompt=(
        "You are a structured-output specialist. The user describes a JSON "
        "schema (or a list of fields they want) and optionally a source — "
        "raw text, or one or more image URLs. "
        "If they provide image URLs call extract_from_images. Otherwise call "
        "extract_from_text with the body of text and the desired schema. "
        "Always return strictly valid JSON — no markdown fences, no commentary. "
        "Default model: anthropic/claude-sonnet-4.6 via OpenRouter. "
        "Priced per-token through fal.ai (see OpenRouter rate card)."
    ),
    capabilities=["structured_output"],
    default_config={
        "capability": "structured_output",
        "model": "anthropic/claude-sonnet-4.6",
    },
)

structured_output_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@structured_output_agent.tool
async def extract_from_text(
    ctx: RunContext[OrchestratorDeps],
    text: str,
    schema_description: str,
) -> str:
    """Extract JSON from raw text following the described schema."""
    model = ctx.deps.model or "anthropic/claude-sonnet-4.6"
    prompt = (
        "Return ONLY valid JSON matching this schema:\n"
        f"{schema_description}\n\n"
        "Source text:\n"
        f"{text}"
    )
    return await fal_client.any_llm_completion(prompt, model=model)


@structured_output_agent.tool
async def extract_from_images(
    ctx: RunContext[OrchestratorDeps],
    image_urls: list[str],
    schema_description: str,
) -> str:
    """Extract JSON from images (OCR, attribute extraction, etc.)."""
    model = ctx.deps.model or "anthropic/claude-sonnet-4.6"
    prompt = (
        "Return ONLY valid JSON matching this schema:\n"
        f"{schema_description}\n\n"
        "Read the supplied images and extract the fields."
    )
    return await fal_client.analyze_image(image_urls, prompt, model=model)
