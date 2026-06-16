# tests/test_fal_client.py
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch
from media_agents.agents.client import FalClient


@pytest.fixture
def client():
    return FalClient()


async def test_any_llm_completion_returns_output(client):
    with patch("media_agents.agents.client._fal") as m:
        m.run_async = AsyncMock(return_value={"output": "hello from llm"})
        result = await client.any_llm_completion(
            prompt="say hello", model="google/gemini-2.5-flash"
        )
    assert result == "hello from llm"
    assert m.run_async.call_args[0][0] == "openrouter/router"


async def test_analyze_image_returns_output(client):
    with patch("media_agents.agents.client._fal") as m:
        m.run_async = AsyncMock(return_value={"output": "a tiger photo"})
        result = await client.analyze_image(
            image_urls=["https://example.com/img.jpg"], prompt="describe this"
        )
    assert result == "a tiger photo"
    assert m.run_async.call_args[0][0] == "openrouter/router/vision"


async def test_analyze_video_returns_output(client):
    with patch("media_agents.agents.client._fal") as m:
        m.run_async = AsyncMock(return_value={"output": "a person walking"})
        result = await client.analyze_video(
            video_urls=["https://example.com/vid.mp4"], prompt="describe this video"
        )
    assert result == "a person walking"
    assert m.run_async.call_args[0][0] == "openrouter/router/video/enterprise"


async def test_generate_music_returns_audio_url(client):
    with patch("media_agents.agents.client._fal") as m:
        m.run_async = AsyncMock(
            return_value={"audio": {"url": "https://fal.media/track.mp3"}}
        )
        result = await client.generate_music(prompt="jazz, upbeat")
    assert result == "https://fal.media/track.mp3"
    assert m.run_async.call_args[0][0] == "fal-ai/minimax-music/v2.6"


async def test_generate_music_passes_lyrics(client):
    with patch("media_agents.agents.client._fal") as m:
        m.run_async = AsyncMock(
            return_value={"audio": {"url": "https://fal.media/track.mp3"}}
        )
        await client.generate_music(
            prompt="pop", lyrics="[verse]\nhello world", is_instrumental=False
        )
    args = m.run_async.call_args[1]["arguments"]
    assert args["lyrics"] == "[verse]\nhello world"
    assert args["is_instrumental"] is False


async def test_generate_3d_from_text_returns_urls(client):
    with patch("media_agents.agents.client._fal") as m:
        m.run_async = AsyncMock(
            return_value={
                "model_glb": {"url": "https://fal.media/model.glb"},
                "thumbnail": {"url": "https://fal.media/thumb.png"},
            }
        )
        result = await client.generate_3d_from_text(prompt="a red cube")
    assert result == {
        "glb_url": "https://fal.media/model.glb",
        "thumbnail_url": "https://fal.media/thumb.png",
    }
    assert m.run_async.call_args[0][0] == "fal-ai/hunyuan3d-v3/text-to-3d"


async def test_generate_3d_from_images_returns_urls(client):
    with patch("media_agents.agents.client._fal") as m:
        m.run_async = AsyncMock(
            return_value={
                "model_mesh": {"url": "https://fal.media/mesh.glb"},
                "thumbnail": {"url": "https://fal.media/thumb.png"},
            }
        )
        result = await client.generate_3d_from_images(
            image_url="https://example.com/front.jpg"
        )
    assert result["model_url"] == "https://fal.media/mesh.glb"
    assert m.run_async.call_args[0][0] == "fal-ai/meshy/v5/multi-image-to-3d"


async def test_remesh_3d_model_returns_url(client):
    with patch("media_agents.agents.client._fal") as m:
        m.run_async = AsyncMock(
            return_value={"model_mesh": {"url": "https://fal.media/remesh.glb"}}
        )
        result = await client.remesh_3d_model(model_url="https://fal.media/input.glb")
    assert result == "https://fal.media/remesh.glb"
    assert m.run_async.call_args[0][0] == "fal-ai/meshy/v5/remesh"


async def test_retexture_3d_model_returns_url(client):
    with patch("media_agents.agents.client._fal") as m:
        m.run_async = AsyncMock(
            return_value={"model_mesh": {"url": "https://fal.media/retex.glb"}}
        )
        result = await client.retexture_3d_model(
            model_url="https://fal.media/input.glb", object_prompt="a wooden chest"
        )
    assert result == "https://fal.media/retex.glb"
    assert m.run_async.call_args[0][0] == "fal-ai/meshy/v5/retexture"


async def test_generate_human_motion_returns_url(client):
    with patch("media_agents.agents.client._fal") as m:
        m.run_async = AsyncMock(
            return_value={"video": {"url": "https://fal.media/motion.mp4"}}
        )
        result = await client.generate_human_motion(prompt="a person waving")
    assert result == "https://fal.media/motion.mp4"
    assert m.run_async.call_args[0][0] == "fal-ai/hunyuan-motion/fast"


async def test_any_llm_completion_passes_system_prompt(client):
    with patch("media_agents.agents.client._fal") as m:
        m.run_async = AsyncMock(return_value={"output": "ok"})
        await client.any_llm_completion(
            prompt="hi", model="google/gemini-2.5-flash", system_prompt="be brief"
        )
    args = m.run_async.call_args[1]["arguments"]
    assert args["system_prompt"] == "be brief"


async def test_generate_3d_from_images_passes_optional_views(client):
    with patch("media_agents.agents.client._fal") as m:
        m.run_async = AsyncMock(
            return_value={
                "model_mesh": {"url": "https://fal.media/mesh.glb"},
                "thumbnail": {"url": "https://fal.media/thumb.png"},
            }
        )
        await client.generate_3d_from_images(
            image_url="https://example.com/front.jpg",
            left_image_url="https://example.com/left.jpg",
            back_image_url="https://example.com/back.jpg",
        )
    args = m.run_async.call_args[1]["arguments"]
    assert args["left_image_url"] == "https://example.com/left.jpg"
    assert args["back_image_url"] == "https://example.com/back.jpg"
    assert "right_image_url" not in args


async def test_retexture_3d_model_passes_style_prompt(client):
    with patch("media_agents.agents.client._fal") as m:
        m.run_async = AsyncMock(
            return_value={"model_mesh": {"url": "https://fal.media/retex.glb"}}
        )
        await client.retexture_3d_model(
            model_url="https://fal.media/input.glb",
            object_prompt="a chest",
            style_prompt="aged oak",
        )
    args = m.run_async.call_args[1]["arguments"]
    assert args["style_prompt"] == "aged oak"
