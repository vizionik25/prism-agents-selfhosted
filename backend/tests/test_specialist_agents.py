# tests/test_specialist_agents.py
from __future__ import annotations
import uuid
import json
from unittest.mock import patch
from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.messages import ModelResponse, ToolCallPart, TextPart
from media_agents.agents.deps import OrchestratorDeps


def _deps() -> OrchestratorDeps:
    return OrchestratorDeps(
        user_id=uuid.uuid4(), board_id=uuid.uuid4(), system_prompt=""
    )


# ── chat_openai ──────────────────────────────────────────────────────────────


def test_chat_openai_template_capability():
    from media_agents.agents.specialist.chat_openai import TEMPLATE

    assert TEMPLATE.capabilities[0] == "openrouter_chat"
    assert TEMPLATE.default_config.get("capability") == "openrouter_chat"


async def test_chat_openai_agent_returns_text():
    from media_agents.agents.specialist.chat_openai import chat_openai_agent

    with chat_openai_agent.override(
        model=TestModel(custom_output_text="reply", call_tools=[])
    ):
        result = await chat_openai_agent.run("hello", deps=_deps())
    assert result.output == "reply"


# ── any_llm ──────────────────────────────────────────────────────────────────


def test_any_llm_template_capability():
    from media_agents.agents.specialist.any_llm import TEMPLATE

    assert TEMPLATE.capabilities[0] == "any_llm"
    assert TEMPLATE.default_config.get("capability") == "any_llm"


async def test_any_llm_tool_calls_fal_client():
    from media_agents.agents.specialist.any_llm import any_llm_agent
    from media_agents.agents.specialist import any_llm as any_llm_mod

    captured = {}

    async def fake_any_llm_completion(prompt, model, system_prompt=""):
        captured["prompt"] = prompt
        return "the answer is 42"

    call_count = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="query_llm",
                        args=json.dumps({"prompt": "what is 6x7"}),
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="the answer is 42")])

    with patch.object(
        any_llm_mod.fal_client, "any_llm_completion", fake_any_llm_completion
    ):
        with any_llm_agent.override(model=FunctionModel(model_fn)):
            await any_llm_agent.run("what is 6x7", deps=_deps())

    assert captured["prompt"] == "what is 6x7"


# ── vision ───────────────────────────────────────────────────────────────────


def test_vision_template_capability():
    from media_agents.agents.specialist.vision import TEMPLATE

    assert TEMPLATE.capabilities[0] == "vision"
    assert TEMPLATE.default_config.get("capability") == "vision"


async def test_vision_tool_calls_analyze_image():
    from media_agents.agents.specialist.vision import vision_agent
    from media_agents.agents.specialist import vision as vision_mod

    captured = {}

    async def fake_analyze_image(image_urls, prompt, model="google/gemini-2.5-flash"):
        captured["image_urls"] = image_urls
        return "a cat on a mat"

    call_count = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="analyze_image",
                        args=json.dumps(
                            {
                                "image_urls": ["https://example.com/cat.jpg"],
                                "prompt": "what is this?",
                            }
                        ),
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="a cat on a mat")])

    with patch.object(vision_mod.fal_client, "analyze_image", fake_analyze_image):
        with vision_agent.override(model=FunctionModel(model_fn)):
            await vision_agent.run("what is in this image?", deps=_deps())

    assert captured["image_urls"] == ["https://example.com/cat.jpg"]


# ── video_analysis ────────────────────────────────────────────────────────────


def test_video_analysis_template_capability():
    from media_agents.agents.specialist.video_analysis import TEMPLATE

    assert TEMPLATE.capabilities[0] == "video_analysis"
    assert TEMPLATE.default_config.get("capability") == "video_analysis"


async def test_video_analysis_tool_calls_analyze_video():
    from media_agents.agents.specialist.video_analysis import video_analysis_agent
    from media_agents.agents.specialist import video_analysis as video_analysis_mod

    captured = {}

    async def fake_analyze_video(video_urls, prompt, model="google/gemini-2.5-flash"):
        captured["video_urls"] = video_urls
        return "a person walking"

    call_count = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="analyze_video",
                        args=json.dumps(
                            {
                                "video_urls": ["https://example.com/vid.mp4"],
                                "prompt": "describe",
                            }
                        ),
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="a person walking")])

    with patch.object(
        video_analysis_mod.fal_client, "analyze_video", fake_analyze_video
    ):
        with video_analysis_agent.override(model=FunctionModel(model_fn)):
            await video_analysis_agent.run("what happens in this video?", deps=_deps())

    assert captured["video_urls"] == ["https://example.com/vid.mp4"]


# ── music ─────────────────────────────────────────────────────────────────────


def test_music_template_capability():
    from media_agents.agents.specialist.music import TEMPLATE

    assert TEMPLATE.capabilities[0] == "music_generation"
    assert TEMPLATE.default_config.get("capability") == "music_generation"


async def test_music_tool_appends_url_to_deps():
    from media_agents.agents.specialist.music import music_agent
    from media_agents.agents.specialist import music as music_mod

    async def fake_generate_music(prompt, lyrics="", is_instrumental=False, **kwargs):
        return "https://fal.media/track.mp3"

    call_count = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="generate_music",
                        args=json.dumps({"prompt": "jazz, upbeat 120bpm"}),
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="Here is your jazz track")])

    with patch.object(music_mod.fal_client, "generate_music", fake_generate_music):
        deps = _deps()
        with music_agent.override(model=FunctionModel(model_fn)):
            await music_agent.run("make me a jazz track", deps=deps)

    assert "https://fal.media/track.mp3" in deps.asset_urls


# ── human_motion ──────────────────────────────────────────────────────────────


def test_human_motion_template_capability():
    from media_agents.agents.specialist.human_motion import TEMPLATE

    assert TEMPLATE.capabilities[0] == "human_motion"
    assert TEMPLATE.default_config.get("capability") == "human_motion"


async def test_human_motion_tool_appends_url_to_deps():
    from media_agents.agents.specialist.human_motion import human_motion_agent
    from media_agents.agents.specialist import human_motion as human_motion_mod

    async def fake_generate_human_motion(prompt, **kwargs):
        return "https://fal.media/motion.mp4"

    call_count = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="generate_human_motion",
                        args=json.dumps({"prompt": "a person doing a cartwheel"}),
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="Generated 3D motion")])

    with patch.object(
        human_motion_mod.fal_client, "generate_human_motion", fake_generate_human_motion
    ):
        deps = _deps()
        with human_motion_agent.override(model=FunctionModel(model_fn)):
            await human_motion_agent.run("cartwheel motion", deps=deps)

    assert "https://fal.media/motion.mp4" in deps.asset_urls


# ── text_to_3d ────────────────────────────────────────────────────────────────


def test_text_to_3d_template_capability():
    from media_agents.agents.specialist.text_to_3d import TEMPLATE

    assert TEMPLATE.capabilities[0] == "text_to_3d"
    assert TEMPLATE.default_config.get("capability") == "text_to_3d"


async def test_text_to_3d_tool_appends_both_urls():
    from media_agents.agents.specialist.text_to_3d import text_to_3d_agent
    from media_agents.agents.specialist import text_to_3d as text_to_3d_mod

    async def fake_generate_3d(
        prompt, generate_type="Normal", enable_pbr=False, **kwargs
    ):
        return {
            "glb_url": "https://fal.media/model.glb",
            "thumbnail_url": "https://fal.media/thumb.png",
        }

    call_count = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="generate_3d_model",
                        args=json.dumps({"prompt": "a red cube"}),
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="Here is your 3D model")])

    with patch.object(
        text_to_3d_mod.fal_client, "generate_3d_from_text", fake_generate_3d
    ):
        deps = _deps()
        with text_to_3d_agent.override(model=FunctionModel(model_fn)):
            await text_to_3d_agent.run("create a 3D red cube", deps=deps)

    assert "https://fal.media/model.glb" in deps.asset_urls
    assert "https://fal.media/thumb.png" in deps.asset_urls


# ── image_to_3d ───────────────────────────────────────────────────────────────


def test_image_to_3d_template_capability():
    from media_agents.agents.specialist.image_to_3d import TEMPLATE

    assert TEMPLATE.capabilities[0] == "image_to_3d"
    assert TEMPLATE.default_config.get("capability") == "image_to_3d"


async def test_image_to_3d_tool_appends_both_urls():
    from media_agents.agents.specialist.image_to_3d import image_to_3d_agent
    from media_agents.agents.specialist import image_to_3d as image_to_3d_mod

    async def fake_generate_3d_from_images(
        image_url, left_image_url="", back_image_url="", right_image_url="", **kwargs
    ):
        return {
            "model_url": "https://fal.media/mesh.glb",
            "thumbnail_url": "https://fal.media/thumb.png",
        }

    call_count = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="generate_3d_from_images",
                        args=json.dumps({"image_url": "https://example.com/front.jpg"}),
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="Here is your 3D model")])

    with patch.object(
        image_to_3d_mod.fal_client,
        "generate_3d_from_images",
        fake_generate_3d_from_images,
    ):
        deps = _deps()
        with image_to_3d_agent.override(model=FunctionModel(model_fn)):
            await image_to_3d_agent.run("turn this image into 3D", deps=deps)

    assert "https://fal.media/mesh.glb" in deps.asset_urls
    assert "https://fal.media/thumb.png" in deps.asset_urls


# ── remesh_3d ─────────────────────────────────────────────────────────────────


def test_remesh_3d_template_capability():
    from media_agents.agents.specialist.remesh_3d import TEMPLATE

    assert TEMPLATE.capabilities[0] == "remesh_3d"
    assert TEMPLATE.default_config.get("capability") == "remesh_3d"


async def test_remesh_3d_tool_appends_url():
    from media_agents.agents.specialist.remesh_3d import remesh_3d_agent
    from media_agents.agents.specialist import remesh_3d as remesh_3d_mod

    async def fake_remesh(model_url, target_count=50000, **kwargs):
        return "https://fal.media/remesh.glb"

    call_count = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="remesh_model",
                        args=json.dumps({"model_url": "https://fal.media/input.glb"}),
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="Remeshed model ready")])

    with patch.object(remesh_3d_mod.fal_client, "remesh_3d_model", fake_remesh):
        deps = _deps()
        with remesh_3d_agent.override(model=FunctionModel(model_fn)):
            await remesh_3d_agent.run("remesh this model", deps=deps)

    assert "https://fal.media/remesh.glb" in deps.asset_urls


# ── retexture_3d ──────────────────────────────────────────────────────────────


def test_retexture_3d_template_capability():
    from media_agents.agents.specialist.retexture_3d import TEMPLATE

    assert TEMPLATE.capabilities[0] == "retexture_3d"
    assert TEMPLATE.default_config.get("capability") == "retexture_3d"


async def test_retexture_3d_tool_appends_url():
    from media_agents.agents.specialist.retexture_3d import retexture_3d_agent
    from media_agents.agents.specialist import retexture_3d as retexture_3d_mod

    async def fake_retexture(model_url, object_prompt, style_prompt="", **kwargs):
        return "https://fal.media/retex.glb"

    call_count = {"n": 0}

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="retexture_model",
                        args=json.dumps(
                            {
                                "model_url": "https://fal.media/input.glb",
                                "object_prompt": "a wooden chest",
                                "style_prompt": "aged oak",
                            }
                        ),
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(content="Retextured model ready")])

    with patch.object(
        retexture_3d_mod.fal_client, "retexture_3d_model", fake_retexture
    ):
        deps = _deps()
        with retexture_3d_agent.override(model=FunctionModel(model_fn)):
            await retexture_3d_agent.run("retexture with wood", deps=deps)

    assert "https://fal.media/retex.glb" in deps.asset_urls


# ── registry ──────────────────────────────────────────────────────────────────


def test_registry_contains_all_10_specialists():
    # Core 10 specialists must be present; the registry may have grown to
    # include additional specialists + back-compat aliases, so this asserts
    # a subset rather than exact equality.
    from media_agents.agents.specialist import SPECIALIST_REGISTRY

    expected_keys = {
        "openrouter_chat",
        "any_llm",
        "vision",
        "video_analysis",
        "music_generation",
        "text_to_3d",
        "image_to_3d",
        "remesh_3d",
        "retexture_3d",
        "human_motion",
    }
    assert expected_keys <= set(SPECIALIST_REGISTRY.keys())


def test_registry_values_are_pydantic_ai_agents():
    from media_agents.agents.specialist import SPECIALIST_REGISTRY
    from pydantic_ai import Agent

    for key, agent in SPECIALIST_REGISTRY.items():
        assert isinstance(agent, Agent), f"{key} is not an Agent"


# ── template registration ─────────────────────────────────────────────────────


def test_all_specialist_templates_in_default_templates():
    # "image" and "video" are back-compat aliases in the registry that map
    # to text_to_image_agent / text_to_video_agent; they intentionally do
    # not have templates under the alias name.
    _BACKCOMPAT_ALIASES = {"image", "video"}
    from media_agents.agents.templates import get_all_templates
    from media_agents.agents.specialist import SPECIALIST_REGISTRY

    capability_tags = {cap for t in get_all_templates() for cap in t.capabilities}
    for key in SPECIALIST_REGISTRY:
        if key in _BACKCOMPAT_ALIASES:
            continue
        assert key in capability_tags, f"capability {key!r} not in DEFAULT_TEMPLATES"


def test_specialist_template_default_config_has_capability_key():
    from media_agents.agents.templates import get_all_templates
    from media_agents.agents.specialist import SPECIALIST_REGISTRY

    for t in get_all_templates():
        cap = t.capabilities[0] if t.capabilities else None
        if cap in SPECIALIST_REGISTRY:
            assert t.default_config.get("capability") == cap, (
                f"Template {t.name!r} missing capability key in default_config"
            )
