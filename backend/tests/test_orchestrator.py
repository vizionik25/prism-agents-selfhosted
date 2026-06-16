"""Tests for AgentOrchestrator command parsing and stream() dispatch.

The orchestrator's only contract with the rest of the system is its prefix-tagged
output (TEXT:/URL:/STATUS:/ERROR:). These tests lock that contract in.

For free-form input (no slash command), we replace the underlying PydanticAI
agent's model with a TestModel/FunctionModel via `luma_agent.override(...)` so we
never touch fal.ai during tests.
"""

from __future__ import annotations

import uuid
from typing import AsyncGenerator

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from media_agents.agents import orchestrator as orch_module
from media_agents.agents.orchestrator import AgentOrchestrator, luma_agent


# ---- _parse_command --------------------------------------------------------


@pytest.mark.parametrize(
    "message, expected",
    [
        ("hello world", None),
        ("/help", {"type": "help"}),
        ("/HELP", {"type": "help"}),
        ("/image a sunset", {"type": "image", "prompt": "a sunset"}),
        ("/IMAGE a sunset", {"type": "image", "prompt": "a sunset"}),
        ("/video a city", {"type": "video", "prompt": "a city"}),
        ("/research llm trends", {"type": "research", "query": "llm trends"}),
        # Regression: /create_agent had a 13/14 off-by-one — the description
        # used to start with a leading space.
        (
            "/create_agent a marketing copywriter",
            {"type": "create_agent", "description": "a marketing copywriter"},
        ),
    ],
)
def test_parse_command(message: str, expected: dict | None) -> None:
    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    assert o._parse_command(message) == expected


def test_parse_command_unknown_slash_returns_none() -> None:
    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    assert o._parse_command("/unknown foo") is None


# ---- system prompt selection -----------------------------------------------


def test_default_system_prompt() -> None:
    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    assert o._get_system_prompt() == orch_module.SYSTEM_PROMPT
    assert o.custom_agent is None


def test_custom_system_prompt_takes_precedence() -> None:
    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    o.set_custom_agent("you are a pirate", {"foo": "bar"})
    assert o._get_system_prompt() == "you are a pirate"
    assert o.custom_agent is not None
    assert o.custom_agent.default_config == {"foo": "bar"}


# ---- stream() — slash command fast paths -----------------------------------


async def _collect(gen: AsyncGenerator[str, None]) -> list[str]:
    return [chunk async for chunk in gen]


async def test_stream_image_command_fast_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Slash command bypasses the LLM and calls fal_client directly."""

    async def fake_generate_image(prompt: str, model: str = "") -> str:
        return f"https://fal.example/img/{prompt.replace(' ', '_')}.png"

    monkeypatch.setattr(orch_module.fal_client, "generate_image", fake_generate_image)

    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    chunks = await _collect(o.stream("/image a sunset", []))

    assert chunks[0] == "STATUS:processing"
    assert "URL:https://fal.example/img/a_sunset.png" in chunks
    assert chunks[-1] == "STATUS:completed"


async def test_stream_image_command_emits_error_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(prompt: str, model: str = "") -> str:
        raise RuntimeError("fal exploded")

    monkeypatch.setattr(orch_module.fal_client, "generate_image", boom)

    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    chunks = await _collect(o.stream("/image x", []))

    assert any(c.startswith("ERROR:") and "fal exploded" in c for c in chunks)
    assert chunks[-1] == "STATUS:completed"


async def test_stream_help_yields_help_text() -> None:
    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    chunks = await _collect(o.stream("/help", []))

    text_chunks = [c[5:] for c in chunks if c.startswith("TEXT:")]
    assert text_chunks, "expected at least one TEXT chunk"
    assert "Available commands" in text_chunks[0]
    assert chunks[-1] == "STATUS:completed"


# ---- stream() — free-form input through the PydanticAI agent ---------------


async def test_stream_free_form_text_response() -> None:
    """Plain text input (no slash) goes through luma_agent → TestModel returns text.

    `call_tools=[]` suppresses TestModel's default behavior of invoking every
    registered tool — we want a pure text response here.
    """
    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())

    test_model = TestModel(custom_output_text="hello back", call_tools=[])
    with luma_agent.override(model=test_model):
        chunks = await _collect(o.stream("hi there", []))

    assert chunks[0] == "STATUS:processing"
    assert "TEXT:hello back" in chunks
    assert chunks[-1] == "STATUS:completed"


async def test_stream_free_form_invokes_image_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Free-form input that triggers the image tool yields a URL chunk."""

    async def fake_generate_image(prompt: str, model: str = "") -> str:
        return "https://fal.example/img/llm-decided.png"

    monkeypatch.setattr(orch_module.fal_client, "generate_image", fake_generate_image)

    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    # FunctionModel that calls generate_image on the first turn, then returns text.
    call_count = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="generate_image",
                        args='{"prompt": "a robot"}',
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="here is the image")])

    with luma_agent.override(model=FunctionModel(model_fn)):
        chunks = await _collect(o.stream("make me an image of a robot", []))

    assert chunks[0] == "STATUS:processing"
    assert "URL:https://fal.example/img/llm-decided.png" in chunks
    assert "TEXT:here is the image" in chunks
    assert chunks[-1] == "STATUS:completed"


async def test_stream_free_form_agent_error_yields_error_chunk() -> None:
    def boom(messages, info: AgentInfo) -> ModelResponse:
        raise RuntimeError("model unavailable")

    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    with luma_agent.override(model=FunctionModel(boom)):
        chunks = await _collect(o.stream("hello", []))

    assert any(c.startswith("ERROR:") for c in chunks)
    assert chunks[-1] == "STATUS:completed"


async def test_custom_agent_prompt_reaches_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The custom agent's system prompt must be visible to the underlying model."""
    captured_system: list[str] = []

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        captured_system.append(info.instructions or "")
        return ModelResponse(parts=[TextPart(content="ok")])

    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    o.set_custom_agent("you are a pirate, talk like one", {})

    with luma_agent.override(model=FunctionModel(model_fn)):
        await _collect(o.stream("hello", []))

    assert any("pirate" in s for s in captured_system), captured_system


# ── specialist delegation ─────────────────────────────────────────────────────


def test_set_custom_agent_reads_capability_from_config() -> None:
    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    o.set_custom_agent("some prompt", {"capability": "music_generation"})
    assert o.custom_agent is not None
    assert o.custom_agent.capabilities[0] == "music_generation"


def test_set_custom_agent_defaults_capability_to_custom() -> None:
    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    o.set_custom_agent("some prompt", {})
    assert o.custom_agent.capabilities[0] == "custom"


async def test_stream_delegates_to_music_specialist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from media_agents.agents.specialist.music import music_agent
    from media_agents.agents.specialist import music as music_mod

    async def fake_generate_music(
        prompt: str, lyrics: str = "", is_instrumental: bool = False, **kwargs
    ) -> str:
        return "https://fal.example/track.mp3"

    monkeypatch.setattr(music_mod.fal_client, "generate_music", fake_generate_music)

    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    o.set_custom_agent("you are a music specialist", {"capability": "music_generation"})

    call_count = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="generate_music",
                        args='{"prompt": "jazz 120bpm"}',
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="Here is your track")])

    with music_agent.override(model=FunctionModel(model_fn)):
        chunks = await _collect(o.stream("make me jazz music", []))

    assert chunks[0] == "STATUS:processing"
    assert "URL:https://fal.example/track.mp3" in chunks
    assert chunks[-1] == "STATUS:completed"


async def test_stream_falls_back_to_luma_agent_when_no_specialist() -> None:
    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    o.set_custom_agent("you are a copywriter", {"capability": "custom"})
    with luma_agent.override(
        model=TestModel(custom_output_text="copy written", call_tools=[])
    ):
        chunks = await _collect(o.stream("write me copy", []))
    assert "TEXT:copy written" in chunks
    assert chunks[-1] == "STATUS:completed"


# ── new slash command parsing ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "message, expected",
    [
        ("/music jazz at 120bpm", {"type": "music", "prompt": "jazz at 120bpm"}),
        ("/3d a red wooden cube", {"type": "3d", "prompt": "a red wooden cube"}),
        ("/motion a person waving", {"type": "motion", "prompt": "a person waving"}),
        (
            "/vision https://example.com/img.jpg what is this",
            {
                "type": "vision",
                "url": "https://example.com/img.jpg",
                "question": "what is this",
            },
        ),
        (
            "/analyze-video https://example.com/v.mp4 describe it",
            {
                "type": "analyze_video",
                "url": "https://example.com/v.mp4",
                "question": "describe it",
            },
        ),
        (
            "/image-to-3d https://example.com/front.jpg",
            {"type": "image_to_3d", "url": "https://example.com/front.jpg"},
        ),
        (
            "/remesh https://fal.media/model.glb",
            {"type": "remesh", "url": "https://fal.media/model.glb"},
        ),
        (
            "/retexture https://fal.media/model.glb wooden aged oak",
            {
                "type": "retexture",
                "url": "https://fal.media/model.glb",
                "prompt": "wooden aged oak",
            },
        ),
    ],
)
def test_parse_new_commands(message: str, expected: dict) -> None:
    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    assert o._parse_command(message) == expected


async def test_stream_music_command_fast_path(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_generate_music(
        prompt: str, lyrics: str = "", is_instrumental: bool = False
    ) -> str:
        return "https://fal.example/track.mp3"

    monkeypatch.setattr(orch_module.fal_client, "generate_music", fake_generate_music)
    chunks = await _collect(
        AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4()).stream(
            "/music chill lo-fi", []
        )
    )
    assert "URL:https://fal.example/track.mp3" in chunks
    assert chunks[-1] == "STATUS:completed"


async def test_stream_3d_command_fast_path(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_generate_3d(
        prompt: str, generate_type: str = "Normal", enable_pbr: bool = False
    ) -> dict:
        return {
            "glb_url": "https://fal.example/model.glb",
            "thumbnail_url": "https://fal.example/thumb.png",
        }

    monkeypatch.setattr(
        orch_module.fal_client, "generate_3d_from_text", fake_generate_3d
    )
    chunks = await _collect(
        AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4()).stream(
            "/3d a red cube", []
        )
    )
    assert "URL:https://fal.example/model.glb" in chunks
    assert "URL:https://fal.example/thumb.png" in chunks
    assert chunks[-1] == "STATUS:completed"


async def test_stream_help_includes_new_commands() -> None:
    chunks = await _collect(
        AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4()).stream(
            "/help", []
        )
    )
    text = " ".join(c[5:] for c in chunks if c.startswith("TEXT:"))
    for cmd in [
        "/music",
        "/3d",
        "/motion",
        "/vision",
        "/analyze-video",
        "/image-to-3d",
        "/remesh",
        "/retexture",
    ]:
        assert cmd in text, f"{cmd} missing from help output"


# ── team DAG path ─────────────────────────────────────────────────────────────


async def test_stream_team_dag_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end: set_team_from_config + stream() runs planner → executor → synth."""
    import json as _json
    from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    from media_agents.agents import team_planner as planner_mod
    from media_agents.agents import orchestrator as orch_mod

    # Stub credit machinery and user lookup.
    async def fake_deduct(user_id, cmd_type):
        return None

    async def fake_get_user(user_id):
        return {"subscriptionCredits": 9999, "packCredits": 0, "id": str(user_id)}

    from media_agents.services import credits as credits_mod
    from media_agents.services import user as user_mod

    monkeypatch.setattr(credits_mod, "deduct_credits", fake_deduct)
    monkeypatch.setattr(user_mod, "get_user_by_id", fake_get_user)

    # Planner emits a 2-node independent plan.
    plan_dict = {
        "summary": "logo + jingle",
        "nodes": [
            {"id": "n1", "member": "text_to_image", "request": "a blue logo"},
            {"id": "n2", "member": "music_generation", "request": "chill jingle"},
        ],
        "estimated_credits": 1 + 3,
    }

    def planner_model(messages, info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="final_result",
                    args=_json.dumps(plan_dict),
                )
            ]
        )

    def synth_model(messages, info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content="Done — logo and jingle ready.")])

    # Stub the two specialist.run() methods.
    from media_agents.agents import specialist as specialist_pkg

    class _Stub:
        def __init__(self, url):
            self._url = url

        async def run(self, req, *, deps):
            deps.asset_urls.append(self._url)

            class R:
                output = "ok"

            return R()

    stubs = dict(specialist_pkg.SPECIALIST_REGISTRY)
    stubs["text_to_image"] = _Stub("https://fal.example/a.png")  # type: ignore
    stubs["music_generation"] = _Stub("https://fal.example/b.mp3")  # type: ignore
    from media_agents.agents import team_dag_executor as exec_mod

    monkeypatch.setattr(exec_mod, "SPECIALIST_REGISTRY", stubs)

    o = AgentOrchestrator(user_id=uuid.uuid4(), board_id=uuid.uuid4())
    o.set_team_from_config(
        team={
            "name": "T",
            "description": None,
            "members": {
                "capabilities": ["text_to_image", "music_generation"],
                "agent_ids": [],
            },
            "orchestrator": {"system_prompt": "p", "routing_strategy": "llm_routed"},
        },
        custom_agents=[],
    )

    with (
        planner_mod.planner_agent.override(model=FunctionModel(planner_model)),
        orch_mod.synthesizer_agent.override(model=FunctionModel(synth_model)),
    ):
        chunks = await _collect(o.stream("make me a logo and jingle", []))

    assert any(c.startswith("PLAN:") for c in chunks)
    assert "URL:n1:https://fal.example/a.png" in chunks
    assert "URL:n2:https://fal.example/b.mp3" in chunks
    assert "TEXT:Done — logo and jingle ready." in chunks  # unscoped synth
    assert chunks[-1] == "STATUS:completed"
