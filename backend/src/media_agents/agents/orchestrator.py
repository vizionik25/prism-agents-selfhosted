"""Routes user messages through slash-command fast paths or a PydanticAI agent.

Slash commands (`/image`, `/video`, `/research`, `/create_agent`, `/help`) skip
the LLM entirely — deterministic, no token cost, instant response. Free-form
input is handled by `luma_agent`, which can call `generate_image`,
`generate_video`, or `research` tools.

The `stream()` method bridges PydanticAI's run model into the prefix-tagged
chunk protocol consumed by `routers/chat.py`:

    TEXT:<s>    assistant text
    URL:<s>     asset URL produced by a tool call
    STATUS:<s>  processing | completed
    ERROR:<s>   terminal error
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, AsyncGenerator

from pydantic_ai import Agent, RunContext

from media_agents.agents.agent_maker import create_agent_from_description
from media_agents.agents.client import fal_client, ImageTo3DRequest
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.fal_model import (
    fal_chat_model,
    reset_current_attachments,
    set_current_attachments,
)
from media_agents.agents.research import research_task
from media_agents.agents.specialist import SPECIALIST_REGISTRY
from media_agents.agents.team_dag_executor import NodeResult, TeamDagExecutor
from media_agents.agents.team_planner import (
    PlanValidationError,
    TeamPlan,
    plan_team_run,
)
from media_agents.agents.templates import AgentTemplate
from media_agents.services import user as user_service

DAG_MAX_PARALLEL = 5

DEFAULT_TEAM_ORCHESTRATOR_PROMPT = (
    "You are a team orchestrator. Analyze user requests, break them into steps, "
    "and delegate to the most suitable team member via the delegate tool. "
    "Synthesize results into a cohesive response."
)


class _TeamConfig:
    __slots__ = (
        "name",
        "description",
        "capabilities",
        "custom_agents",
        "system_prompt",
        "model",
        "temperature",
        "routing_strategy",
        "max_credits",
    )

    def __init__(
        self,
        *,
        name: str,
        description: str | None,
        capabilities: list[str],
        custom_agents: list[dict[str, Any]],
        system_prompt: str,
        model: str | None,
        temperature: float | None,
        routing_strategy: str,
        max_credits: int | None = None,
    ):
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.custom_agents = custom_agents
        self.system_prompt = system_prompt
        self.model = model
        self.temperature = temperature
        self.routing_strategy = routing_strategy
        self.max_credits = max_credits


# Re-export OrchestratorDeps so existing imports from this module keep working.
__all__ = ["AgentOrchestrator", "OrchestratorDeps", "luma_agent"]


SYSTEM_PROMPT = """You are Luma, an expert creative AI agent. You help users create stunning visual content, write compelling copy, and bring ideas to life.

Capabilities:
- Generate images via the generate_image tool when the user wants a visual
- Generate short videos via the generate_video tool when motion is requested
- Research topics via the research tool when context is needed
- Write copy and creative direction directly

Communication style: professional but friendly, concise, proactive with suggestions.
Always understand the user's goal before calling tools. Ask clarifying questions when needed."""


luma_agent: Agent[OrchestratorDeps, str] = Agent(
    fal_chat_model,
    deps_type=OrchestratorDeps,
)


@luma_agent.instructions
def _resolve_instructions(ctx: RunContext[OrchestratorDeps]) -> str:
    """Pull the active system prompt from deps so a custom agent can override it."""
    return ctx.deps.system_prompt


@luma_agent.tool
async def generate_image(ctx: RunContext[OrchestratorDeps], prompt: str) -> str:
    """Generate an image from a text prompt. Returns the URL of the generated image."""
    model = ctx.deps.model or "fal-ai/flux/schnell"
    url = await fal_client.generate_image(prompt, model=model)
    ctx.deps.asset_urls.append(url)
    return f"Generated image at {url}"


@luma_agent.tool
async def generate_video(ctx: RunContext[OrchestratorDeps], prompt: str) -> str:
    """Generate a short video from a text prompt. Returns the URL of the generated video."""
    model = ctx.deps.model or "fal-ai/kling-video/v1.6/standard/text-to-video"
    url = await fal_client.generate_video(prompt, model=model)
    ctx.deps.asset_urls.append(url)
    return f"Generated video at {url}"


@luma_agent.tool
async def research(ctx: RunContext[OrchestratorDeps], query: str) -> str:
    """Research a topic and return concise findings."""
    return await research_task(query)


# --- Team run synthesizer ---------------------------------------------------
#
# Runs after the team execution DAG completes. Takes the per-node results and
# produces a single coherent message for the user. Pure text without tools.

synthesizer_agent: Agent[None, str] = Agent(
    fal_chat_model,
    deps_type=None,
    instructions=(
        "You summarize the outcome of a team run. The user will see per-node "
        "cards separately — your job is a short synthesis paragraph: mention "
        "what succeeded, what failed, what was skipped, and suggest a next "
        "step only if obvious. Do not repeat URLs — the UI shows them already. "
        "Keep it to 2–4 sentences."
    ),
)


def _format_synthesis_prompt(
    plan: TeamPlan,
    results: dict[str, NodeResult],
) -> str:
    lines: list[str] = [f"Plan: {plan.summary}", ""]
    for node in plan.nodes:
        r = results[node.id]
        lines.append(f"- [{r.state}] {node.member} ({node.id}): {node.request[:80]}")
        if r.state == "failed" and r.error:
            lines.append(f"    error: {r.error}")
        if r.state == "done" and r.output_text:
            snippet = r.output_text[:200]
            lines.append(f"    output: {snippet}")
    return "\n".join(lines)


class AgentOrchestrator:
    def __init__(self, user_id: uuid.UUID, board_id: uuid.UUID):
        self.user_id = user_id
        self.board_id = board_id
        self.custom_agent: AgentTemplate | None = None
        self._team_config: _TeamConfig | None = None

    def set_team_from_config(
        self,
        team: dict[str, Any],
        custom_agents: list[dict[str, Any]],
        *,
        max_credits_override: int | None = None,
    ) -> None:
        """Configure the orchestrator to run as a saved Team.

        team: a Team row dict (camelCase from Prisma) with members + orchestrator JSON.
        custom_agents: hydrated Agent rows for the agent_ids referenced in team.members.
        max_credits_override: per-call override (e.g. from ChatRequest) — wins over the
            team's saved max_credits.
        """
        members = team.get("members") or {}
        orch = team.get("orchestrator") or {}
        capabilities = list(members.get("capabilities") or [])

        # Custom agents in the roster are routed by their underlying capability.
        # Any custom agent that wraps a known capability becomes addressable.
        for ca in custom_agents:
            cap = (ca.get("config") or {}).get("capability")
            if cap and cap in SPECIALIST_REGISTRY and cap not in capabilities:
                capabilities.append(cap)

        max_credits = max_credits_override
        if max_credits is None:
            saved_cap = orch.get("max_credits")
            if isinstance(saved_cap, (int, float)) and saved_cap > 0:
                max_credits = int(saved_cap)

        self._team_config = _TeamConfig(
            name=team.get("name", "Team"),
            description=team.get("description"),
            capabilities=capabilities,
            custom_agents=custom_agents,
            system_prompt=orch.get("system_prompt") or DEFAULT_TEAM_ORCHESTRATOR_PROMPT,
            model=orch.get("model"),
            temperature=orch.get("temperature"),
            routing_strategy=orch.get("routing_strategy") or "llm_routed",
            max_credits=max_credits,
        )

    def set_custom_agent(self, system_prompt: str, config: dict[str, Any]):
        capability = config.get("capability", "custom")
        self.custom_agent = AgentTemplate(
            name="Custom Agent",
            description="User-created custom agent",
            system_prompt=system_prompt,
            capabilities=[capability],
            default_config=config,
        )

    def _get_system_prompt(self) -> str:
        if self.custom_agent:
            return self.custom_agent.system_prompt
        return SYSTEM_PROMPT

    def _get_model(self) -> str | None:
        if self.custom_agent:
            return self.custom_agent.default_config.get("model")
        return None

    def _parse_command(self, message: str) -> dict[str, str] | None:
        stripped = message.strip()
        message_lower = stripped.lower()

        # Simple prefix commands: /cmd <arg>
        prefixes = [
            ("/research ", "research", "query"),
            ("/create_agent ", "create_agent", "description"),
            ("/image ", "image", "prompt"),
            ("/video ", "video", "prompt"),
            ("/music ", "music", "prompt"),
            ("/3d ", "3d", "prompt"),
            ("/motion ", "motion", "prompt"),
        ]
        for prefix, cmd_type, arg_key in prefixes:
            if message_lower.startswith(prefix):
                return {"type": cmd_type, arg_key: stripped[len(prefix) :]}

        # /tts <text>  (speech synthesis)
        if message_lower.startswith("/tts "):
            return {"type": "tts", "text": stripped[len("/tts ") :]}

        # URL-first commands: /cmd <url> [<question-or-arg>]
        for prefix, cmd_type in [
            ("/vision ", "vision"),
            ("/analyze-video ", "analyze_video"),
            ("/image-to-3d ", "image_to_3d"),
            ("/remesh ", "remesh"),
            ("/transcribe ", "transcribe"),
            ("/stems ", "stems"),
            ("/foley ", "foley"),
        ]:
            if message_lower.startswith(prefix):
                rest = stripped[len(prefix) :]
                parts = rest.split(" ", 1)
                result: dict[str, str] = {"type": cmd_type, "url": parts[0]}
                if len(parts) > 1 and parts[1]:
                    result["question"] = parts[1]
                return result

        # /retexture <url> <prompt>
        if message_lower.startswith("/retexture "):
            rest = stripped[len("/retexture ") :]
            parts = rest.split(" ", 1)
            return {
                "type": "retexture",
                "url": parts[0],
                "prompt": parts[1] if len(parts) > 1 else "",
            }

        # /edit <image_url> <prompt>
        if message_lower.startswith("/edit "):
            rest = stripped[len("/edit ") :]
            parts = rest.split(" ", 1)
            return {
                "type": "edit_image",
                "url": parts[0],
                "prompt": parts[1] if len(parts) > 1 else "",
            }

        # /animate <image_url> <prompt>
        if message_lower.startswith("/animate "):
            rest = stripped[len("/animate ") :]
            parts = rest.split(" ", 1)
            return {
                "type": "animate",
                "url": parts[0],
                "prompt": parts[1] if len(parts) > 1 else "",
            }

        # /lipsync <video_url> <audio_url>
        if message_lower.startswith("/lipsync "):
            rest = stripped[len("/lipsync ") :]
            parts = rest.split(" ", 1)
            return {
                "type": "lipsync",
                "video_url": parts[0],
                "audio_url": parts[1].strip() if len(parts) > 1 else "",
            }

        # /avatar <image_url> <audio_url> [<prompt>]
        if message_lower.startswith("/avatar "):
            rest = stripped[len("/avatar ") :]
            parts = rest.split(" ", 2)
            return {
                "type": "avatar",
                "url": parts[0],
                "audio_url": parts[1] if len(parts) > 1 else "",
                "prompt": parts[2] if len(parts) > 2 else "a calm speaker",
            }

        if message_lower.startswith("/help"):
            return {"type": "help"}

        return None

    async def stream(
        self,
        message: str,
        history: list[dict[str, str]],
        attachments: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        command = self._parse_command(message)

        if command:
            yield "STATUS:processing"
            async for chunk in self._handle_command(command, model=self._get_model()):
                yield chunk
            return

        # ── Team execution path (planner → DAG executor → synthesizer) ──
        if self._team_config is not None:
            yield "STATUS:processing"

            user = await user_service.get_user_by_id(self.user_id)
            user_balance = (
                (user.get("subscriptionCredits") or 0) + (user.get("packCredits") or 0)
                if user
                else 0
            )

            try:
                plan = await plan_team_run(
                    message=message,
                    team_name=self._team_config.name,
                    capabilities=self._team_config.capabilities,
                    custom_agents=self._team_config.custom_agents,
                    routing_strategy=self._team_config.routing_strategy,
                    model=self._team_config.model,
                    temperature=self._team_config.temperature,
                    user_balance=user_balance,
                    max_credits=self._team_config.max_credits,
                )
            except PlanValidationError as e:
                yield f"ERROR:{e}"
                yield "STATUS:completed"
                return
            except Exception as e:
                yield f"ERROR:Planner failed: {e}"
                yield "STATUS:completed"
                return

            # Peek event — UI shows the plan as a collapsible card.
            yield f"PLAN:{plan.model_dump_json()}"

            deps = OrchestratorDeps(
                user_id=self.user_id,
                board_id=self.board_id,
                system_prompt="",
                max_credits=self._team_config.max_credits,
                attachments=[
                    {
                        "filename": a["filename"],
                        "mime_type": a["mime_type"],
                        "data_url": a["data_url"],
                    }
                    for a in (attachments or [])
                ],
            )
            queue: asyncio.Queue[str] = asyncio.Queue()
            executor = TeamDagExecutor(plan, deps, queue, max_parallel=DAG_MAX_PARALLEL)

            run_task = asyncio.create_task(executor.run())

            # Drain events as they arrive; flush remaining events when the
            # run finishes so nothing is dropped.
            while True:
                getter = asyncio.create_task(queue.get())
                done, _ = await asyncio.wait(
                    {run_task, getter},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if getter in done:
                    yield getter.result()
                else:
                    getter.cancel()
                if run_task.done() and queue.empty():
                    break

            try:
                results = run_task.result()
            except Exception as e:
                yield f"ERROR:Executor crashed: {e}"
                yield "STATUS:completed"
                return

            # Synthesis — unscoped TEXT (no node_id) → main thread bubble.
            try:
                synth = await synthesizer_agent.run(
                    _format_synthesis_prompt(plan, results)
                )
                if synth.output:
                    yield f"TEXT:{synth.output}"
            except Exception as e:
                # Synthesis is best-effort — the real outputs are already streamed.
                yield f"TEXT:(synthesis unavailable: {e})"

            yield "STATUS:completed"
            return

        # Free-form input — delegate to specialist based on active capability in registry.
        yield "STATUS:processing"
        active_cap = (
            self.custom_agent.capabilities[0]
            if self.custom_agent and self.custom_agent.capabilities
            else None
        )
        target_agent = (
            SPECIALIST_REGISTRY.get(active_cap) if active_cap else None
        ) or luma_agent

        deps = OrchestratorDeps(
            user_id=self.user_id,
            board_id=self.board_id,
            # luma_agent reads this via its @luma_agent.instructions resolver.
            # Specialist agents use their own static TEMPLATE.system_prompt instead.
            system_prompt=self._get_system_prompt(),
            model=self.custom_agent.default_config.get("model")
            if self.custom_agent
            else None,
            attachments=[
                {
                    "filename": a["filename"],
                    "mime_type": a["mime_type"],
                    "data_url": a["data_url"],
                }
                for a in (attachments or [])
            ],
        )
        token = set_current_attachments(attachments)
        try:
            result = await target_agent.run(message, deps=deps)
        except Exception as e:
            yield f"ERROR:{e}"
            yield "STATUS:completed"
            return
        finally:
            reset_current_attachments(token)

        for url in deps.asset_urls:
            yield f"URL:{url}"
        if result.output:
            yield f"TEXT:{result.output}"
        yield "STATUS:completed"

    async def _handle_command(
        self, command: dict[str, str], model: str | None = None
    ) -> AsyncGenerator[str, None]:
        cmd_type = command["type"]

        if cmd_type == "help":
            yield (
                "TEXT:Available commands:\n"
                "\n**Image**\n"
                "/image <prompt> - Generate an image\n"
                "/edit <image_url> <prompt> - Edit an image\n"
                "\n**Video**\n"
                "/video <prompt> - Generate a video from text\n"
                "/animate <image_url> <prompt> - Animate a still image\n"
                "/lipsync <video_url> <audio_url> - Sync lips to new audio\n"
                "/avatar <image_url> <audio_url> <prompt> - Talking-avatar video\n"
                "/analyze-video <url> <question> - Analyze a video\n"
                "\n**Audio**\n"
                "/music <prompt> - Generate a music track\n"
                "/tts <text> - Text-to-speech\n"
                "/transcribe <audio_url> - Transcribe audio (Whisper)\n"
                "/stems <audio_url> - Split a song into stems\n"
                "/foley <video_url> <effect_prompt> - Generate a soundtrack\n"
                "\n**3D**\n"
                "/3d <prompt> - Generate a 3D model from text\n"
                "/image-to-3d <url> - Convert an image to a 3D model\n"
                "/remesh <url> - Optimize polygon count\n"
                "/retexture <url> <prompt> - Apply new textures\n"
                "/motion <prompt> - 3D human motion sequence\n"
                "\n**Other**\n"
                "/vision <url> <question> - Analyze an image\n"
                "/research <query> - Research a topic\n"
                "/create_agent <description> - Create a custom agent\n"
                "/help - Show this help message\n\n"
                "Or just describe what you want to create!"
            )
            yield "STATUS:completed"
            return

        if cmd_type == "research":
            yield "TEXT:Let me research that for you..."
            try:
                result = await research_task(command["query"])
            except Exception as e:
                yield f"ERROR:Research failed: {e}"
                yield "STATUS:completed"
                return
            yield f"TEXT:{result}"
            yield "STATUS:completed"
            return

        if cmd_type == "create_agent":
            yield "TEXT:Creating your custom agent..."
            try:
                agent = await create_agent_from_description(command["description"])
            except Exception as e:
                yield f"ERROR:Failed to create agent: {e}"
                yield "STATUS:completed"
                return
            self.custom_agent = agent
            yield (
                f"TEXT:I've created a custom agent: **{agent.name}**\n\n"
                f"Description: {agent.description}\n\n"
                f"Capabilities: {', '.join(agent.capabilities)}\n\n"
                "You can now use this agent by describing what you want to create."
            )
            yield "STATUS:completed"
            return

        if cmd_type == "image":
            yield "TEXT:Generating your image..."
            try:
                url = await fal_client.generate_image(
                    command["prompt"],
                    model=model or "fal-ai/flux/schnell",
                )
            except Exception as e:
                yield f"ERROR:Failed to generate image: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Here's your generated image!"
            yield f"URL:{url}"
            yield "STATUS:completed"
            return

        if cmd_type == "video":
            yield "TEXT:Generating your video (this may take a moment)..."
            try:
                url = await fal_client.generate_video(command["prompt"])
            except Exception as e:
                yield f"ERROR:Failed to generate video: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Here's your generated video!"
            yield f"URL:{url}"
            yield "STATUS:completed"
            return

        if cmd_type == "music":
            yield "TEXT:Generating your music track..."
            try:
                url = await fal_client.generate_music(command["prompt"])
            except Exception as e:
                yield f"ERROR:Failed to generate music: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Here is your generated music track!"
            yield f"URL:{url}"
            yield "STATUS:completed"
            return

        if cmd_type == "3d":
            yield "TEXT:Generating your 3D model (this may take a moment)..."
            try:
                urls = await fal_client.generate_3d_from_text(command["prompt"])
            except Exception as e:
                yield f"ERROR:Failed to generate 3D model: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Here is your generated 3D model!"
            if urls["glb_url"]:
                yield f"URL:{urls['glb_url']}"
            if urls["thumbnail_url"]:
                yield f"URL:{urls['thumbnail_url']}"
            yield "STATUS:completed"
            return

        if cmd_type == "motion":
            yield "TEXT:Generating your 3D motion sequence..."
            try:
                url = await fal_client.generate_human_motion(command["prompt"])
            except Exception as e:
                yield f"ERROR:Failed to generate motion: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Here is your 3D motion sequence!"
            yield f"URL:{url}"
            yield "STATUS:completed"
            return

        if cmd_type == "vision":
            yield "TEXT:Analyzing image..."
            try:
                result = await fal_client.analyze_image(
                    [command["url"]],
                    command.get("question", "Describe this image in detail."),
                    model=model or "anthropic/claude-sonnet-4.6",
                )
            except Exception as e:
                yield f"ERROR:Image analysis failed: {e}"
                yield "STATUS:completed"
                return
            yield f"TEXT:{result}"
            yield "STATUS:completed"
            return

        if cmd_type == "analyze_video":
            yield "TEXT:Analyzing video..."
            try:
                result = await fal_client.analyze_video(
                    [command["url"]],
                    command.get("question", "Describe this video in detail."),
                    model=model or "anthropic/claude-sonnet-4.6",
                )
            except Exception as e:
                yield f"ERROR:Video analysis failed: {e}"
                yield "STATUS:completed"
                return
            yield f"TEXT:{result}"
            yield "STATUS:completed"
            return

        if cmd_type == "image_to_3d":
            yield "TEXT:Converting image to 3D model (this may take a moment)..."
            try:
                request = ImageTo3DRequest(image_url=command["url"])
                urls = await fal_client.generate_3d_from_images(request)
            except Exception as e:
                yield f"ERROR:Failed to generate 3D from image: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Here is your 3D model!"
            if urls["model_url"]:
                yield f"URL:{urls['model_url']}"
            if urls["thumbnail_url"]:
                yield f"URL:{urls['thumbnail_url']}"
            yield "STATUS:completed"
            return

        if cmd_type == "remesh":
            yield "TEXT:Remeshing your 3D model..."
            try:
                url = await fal_client.remesh_3d_model(command["url"])
            except Exception as e:
                yield f"ERROR:Failed to remesh model: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Here is your remeshed model!"
            yield f"URL:{url}"
            yield "STATUS:completed"
            return

        if cmd_type == "retexture":
            yield "TEXT:Retexturing your 3D model..."
            try:
                url = await fal_client.retexture_3d_model(
                    command["url"], command.get("prompt", "")
                )
            except Exception as e:
                yield f"ERROR:Failed to retexture model: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Here is your retextured model!"
            yield f"URL:{url}"
            yield "STATUS:completed"
            return

        if cmd_type == "tts":
            yield "TEXT:Synthesizing speech..."
            try:
                url = await fal_client.generate_speech(command["text"])
            except Exception as e:
                yield f"ERROR:TTS failed: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Here is your generated speech!"
            yield f"URL:{url}"
            yield "STATUS:completed"
            return

        if cmd_type == "transcribe":
            yield "TEXT:Transcribing audio..."
            try:
                text = await fal_client.transcribe_audio(command["url"])
            except Exception as e:
                yield f"ERROR:Transcription failed: {e}"
                yield "STATUS:completed"
                return
            yield f"TEXT:{text}"
            yield "STATUS:completed"
            return

        if cmd_type == "stems":
            yield "TEXT:Separating stems..."
            try:
                stems = await fal_client.separate_stems(command["url"])
            except Exception as e:
                yield f"ERROR:Stem separation failed: {e}"
                yield "STATUS:completed"
                return
            listing = "\n".join(f"- **{k}**: {v}" for k, v in stems.items())
            yield f"TEXT:Separated stems:\n{listing}"
            for url in stems.values():
                yield f"URL:{url}"
            yield "STATUS:completed"
            return

        if cmd_type == "foley":
            yield "TEXT:Generating soundtrack..."
            try:
                urls = await fal_client.generate_video_soundtrack(
                    command["url"],
                    sound_effect_prompt=command.get("question", ""),
                )
            except Exception as e:
                yield f"ERROR:Foley generation failed: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Generated soundtrack."
            if urls["video_url"]:
                yield f"URL:{urls['video_url']}"
            if urls["audio_url"]:
                yield f"URL:{urls['audio_url']}"
            yield "STATUS:completed"
            return

        if cmd_type == "edit_image":
            yield "TEXT:Editing your image..."
            try:
                url = await fal_client.edit_image(
                    command.get("prompt", ""), [command["url"]]
                )
            except Exception as e:
                yield f"ERROR:Image edit failed: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Edited image!"
            yield f"URL:{url}"
            yield "STATUS:completed"
            return

        if cmd_type == "animate":
            yield "TEXT:Animating your image (this may take a moment)..."
            try:
                url = await fal_client.generate_video_from_image(
                    command.get("prompt", ""), command["url"]
                )
            except Exception as e:
                yield f"ERROR:Image-to-video failed: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Here is your animated clip!"
            yield f"URL:{url}"
            yield "STATUS:completed"
            return

        if cmd_type == "lipsync":
            yield "TEXT:Lipsyncing video to audio..."
            try:
                url = await fal_client.lipsync_video(
                    command["video_url"], command["audio_url"]
                )
            except Exception as e:
                yield f"ERROR:Lipsync failed: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Lipsynced video ready!"
            yield f"URL:{url}"
            yield "STATUS:completed"
            return

        if cmd_type == "avatar":
            yield "TEXT:Generating talking avatar (this may take a moment)..."
            try:
                url = await fal_client.generate_avatar_video(
                    command["url"], command["audio_url"], command.get("prompt", "")
                )
            except Exception as e:
                yield f"ERROR:Avatar generation failed: {e}"
                yield "STATUS:completed"
                return
            yield "TEXT:Here is your talking avatar!"
            yield f"URL:{url}"
            yield "STATUS:completed"
            return
