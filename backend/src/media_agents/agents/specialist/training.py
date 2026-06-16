# src/media_agents/agents/specialist/training.py
from __future__ import annotations
from pydantic_ai import Agent, RunContext
from media_agents.agents.client import fal_client
from media_agents.agents.fal_model import fal_chat_model
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.templates import AgentTemplate

TEMPLATE = AgentTemplate(
    name="LoRA Trainer",
    description=(
        "Train a custom FLUX LoRA on your own images — subjects, styles, characters"
    ),
    system_prompt=(
        "You are a LoRA-training specialist powered by FLUX LoRA Fast Training. "
        "Call train_flux_lora with a URL to a ZIP archive of training images "
        "(at least 4, ideally 10-30 consistent shots). Provide a trigger_word — "
        "a unique token the LoRA learns to associate with your subject "
        "(e.g. 'MXRZP person'). "
        "Set is_style=True for styles, False for subjects. "
        "Default model: fal-ai/flux-lora-fast-training (~$2/training, a few "
        "minutes of queue time). "
        "Alternatives: fal-ai/flux-lora-portrait-trainer ($0.0024, optimized "
        "for faces), fal-ai/flux-kontext-trainer ($2.5, Kontext-compatible). "
        "WARN the user about the cost before launching a run."
    ),
    capabilities=["training"],
    default_config={
        "capability": "training",
        "model": "fal-ai/flux-lora-fast-training",
    },
)

training_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
    instructions=TEMPLATE.system_prompt,
)


@training_agent.tool
async def train_flux_lora(
    ctx: RunContext[OrchestratorDeps],
    images_data_url: str,
    trigger_word: str = "",
    steps: int = 1000,
    is_style: bool = False,
) -> str:
    """Train a FLUX LoRA on a zip of images. Returns the LoRA and config URLs."""
    model = ctx.deps.model or "fal-ai/flux-lora-fast-training"
    urls = await fal_client.train_flux_lora(
        images_data_url,
        trigger_word=trigger_word,
        steps=steps,
        is_style=is_style,
        model=model,
    )
    ctx.deps.asset_urls.append(urls["lora_url"])
    if urls["config_url"]:
        ctx.deps.asset_urls.append(urls["config_url"])
    return (
        f"Trained LoRA at {urls['lora_url']} "
        f"(config: {urls['config_url']}, trigger_word: {trigger_word or 'none'})"
    )
