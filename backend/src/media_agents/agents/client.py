"""Thin wrapper around fal.ai for asset generation.

Chat completions go through `agents/fal_model.py` instead. This module is the
only place that imports `fal_client` for non-chat surfaces.

`fal_client` reads the `FAL_KEY` env var automatically. Every method here
raises `RuntimeError` when the endpoint returns an unexpected shape rather
than silently returning an empty URL — callers in the orchestrator and
specialist tools turn those into `ERROR:` SSE chunks.

All model IDs and field names here are verified against the fal OpenAPI
schemas at `https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=<id>`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import fal_client as _fal


def _require(value: str, context: str, raw: Any) -> str:
    if not value:
        raise RuntimeError(f"{context} returned no URL (raw response: {raw!r})")
    return value


@dataclass
class ImageTo3DRequest:
    image_url: str
    left_image_url: str = ""
    back_image_url: str = ""
    right_image_url: str = ""


class FalClient:
    # ── Image generation ────────────────────────────────────────────────
    async def generate_image(
        self, prompt: str, model: str = "fal-ai/flux/schnell"
    ) -> str:
        """Text-to-image. Default fal-ai/flux/schnell is ~$0.003/megapixel."""
        result = await _fal.run_async(model, arguments={"prompt": prompt})
        url = (result.get("images") or [{}])[0].get("url", "")
        return _require(url, f"generate_image({model})", result)

    async def edit_image(
        self,
        prompt: str,
        image_urls: list[str],
        model: str = "fal-ai/nano-banana/edit",
    ) -> str:
        """Image-to-image edit. Default fal-ai/nano-banana/edit is $0.039/image."""
        result = await _fal.run_async(
            model, arguments={"prompt": prompt, "image_urls": image_urls}
        )
        url = (result.get("images") or [{}])[0].get("url", "")
        return _require(url, f"edit_image({model})", result)

    # ── Video generation ────────────────────────────────────────────────
    async def generate_video(
        self,
        prompt: str,
        model: str = "fal-ai/kling-video/v1.6/standard/text-to-video",
    ) -> str:
        """Text-to-video. Kling 1.6 standard is a reasonable default; video gen is
        slow (30s-2min) and not cheap — check the model page before picking."""
        result = await _fal.run_async(model, arguments={"prompt": prompt})
        url = result.get("video", {}).get("url", "")
        return _require(url, f"generate_video({model})", result)

    async def generate_video_from_image(
        self,
        prompt: str,
        image_url: str,
        model: str = "fal-ai/kling-video/v1.6/standard/image-to-video",
    ) -> str:
        """Image-to-video — animate a still image from a prompt."""
        result = await _fal.run_async(
            model, arguments={"prompt": prompt, "image_url": image_url}
        )
        url = result.get("video", {}).get("url", "")
        return _require(url, f"generate_video_from_image({model})", result)

    async def lipsync_video(
        self,
        video_url: str,
        audio_url: str,
        model: str = "fal-ai/latentsync",
    ) -> str:
        """Video-to-video lipsync. Default LatentSync is $0.005/second."""
        result = await _fal.run_async(
            model, arguments={"video_url": video_url, "audio_url": audio_url}
        )
        url = result.get("video", {}).get("url", "")
        return _require(url, f"lipsync_video({model})", result)

    # ── Speech ─────────────────────────────────────────────────────────
    async def generate_speech(
        self,
        text: str,
        voice_id: str = "Wise_Woman",
        model: str = "fal-ai/minimax/speech-02-turbo",
    ) -> str:
        """Text-to-speech via MiniMax Speech-02 Turbo ($0.06/run).

        `voice_id` must be a valid MiniMax preset (e.g. 'Wise_Woman',
        'Deep_Voice_Man', 'Friendly_Person'). `output_format='url'` is
        required to get a downloadable URL back instead of hex bytes.
        """
        result = await _fal.run_async(
            model,
            arguments={
                "text": text,
                "voice_setting": {"voice_id": voice_id},
                "output_format": "url",
            },
        )
        url = result.get("audio", {}).get("url", "")
        return _require(url, f"generate_speech({model})", result)

    async def transcribe_audio(
        self,
        audio_url: str,
        task: str = "transcribe",
        language: str | None = None,
        model: str = "fal-ai/whisper",
    ) -> str:
        """Speech-to-text via Whisper. `task` is 'transcribe' or 'translate'."""
        arguments: dict[str, Any] = {"audio_url": audio_url, "task": task}
        if language:
            arguments["language"] = language
        result = await _fal.run_async(model, arguments=arguments)
        text = result.get("text", "")
        if not text:
            raise RuntimeError(
                f"transcribe_audio({model}) returned no text (raw: {result!r})"
            )
        return text

    async def convert_voice(
        self,
        source_audio_url: str,
        target_voice_audio_url: str | None = None,
        model: str = "fal-ai/chatterbox/speech-to-speech",
    ) -> str:
        """Speech-to-speech voice conversion. Optional reference voice."""
        arguments: dict[str, Any] = {"source_audio_url": source_audio_url}
        if target_voice_audio_url:
            arguments["target_voice_audio_url"] = target_voice_audio_url
        result = await _fal.run_async(model, arguments=arguments)
        url = result.get("audio", {}).get("url", "")
        return _require(url, f"convert_voice({model})", result)

    # ── Audio / music ──────────────────────────────────────────────────
    async def generate_music(
        self,
        prompt: str,
        lyrics: str = "",
        is_instrumental: bool = False,
        model: str = "fal-ai/minimax-music/v2.6",
    ) -> str:
        arguments: dict[str, Any] = {
            "prompt": prompt,
            "is_instrumental": is_instrumental,
        }
        if lyrics:
            arguments["lyrics"] = lyrics
        result = await _fal.run_async(model, arguments=arguments)
        url = result.get("audio", {}).get("url", "")
        return _require(url, f"generate_music({model})", result)

    async def separate_stems(
        self,
        audio_url: str,
        output_format: str = "mp3",
        model: str = "fal-ai/demucs",
    ) -> dict[str, str]:
        """Audio-to-audio stem separation. Returns a dict of stem name -> URL."""
        result = await _fal.run_async(
            model,
            arguments={"audio_url": audio_url, "output_format": output_format},
        )
        stems = {
            name: (result.get(name) or {}).get("url", "")
            for name in ("vocals", "drums", "bass", "other", "guitar", "piano")
        }
        stems = {k: v for k, v in stems.items() if v}
        if not stems:
            raise RuntimeError(
                f"separate_stems({model}) returned no stems (raw: {result!r})"
            )
        return stems

    # ── Audio-driven video ─────────────────────────────────────────────
    async def generate_avatar_video(
        self,
        image_url: str,
        audio_url: str,
        prompt: str,
        model: str = "fal-ai/stable-avatar",
    ) -> str:
        """Audio-to-video avatar. $0.10/generation on Stable Avatar."""
        result = await _fal.run_async(
            model,
            arguments={
                "image_url": image_url,
                "audio_url": audio_url,
                "prompt": prompt,
            },
        )
        url = result.get("video", {}).get("url", "") or result.get("url", "")
        return _require(url, f"generate_avatar_video({model})", result)

    async def generate_video_soundtrack(
        self,
        video_url: str,
        sound_effect_prompt: str = "",
        background_music_prompt: str = "",
        model: str = "fal-ai/kling-video/video-to-audio",
    ) -> dict[str, str]:
        """Video-to-audio foley. Returns {video_url, audio_url} — the dubbed
        video and the generated audio track."""
        arguments: dict[str, Any] = {"video_url": video_url}
        if sound_effect_prompt:
            arguments["sound_effect_prompt"] = sound_effect_prompt
        if background_music_prompt:
            arguments["background_music_prompt"] = background_music_prompt
        result = await _fal.run_async(model, arguments=arguments)
        video = (result.get("video") or {}).get("url", "")
        audio = (result.get("audio") or {}).get("url", "")
        if not (video or audio):
            raise RuntimeError(
                f"generate_video_soundtrack({model}) returned nothing (raw: {result!r})"
            )
        return {"video_url": video, "audio_url": audio}

    # ── Chat / vision / video analysis ─────────────────────────────────
    async def any_llm_completion(
        self,
        prompt: str,
        model: str = "anthropic/claude-sonnet-4.6",
        system_prompt: str = "",
    ) -> str:
        payload: dict[str, Any] = {"prompt": prompt, "model": model}
        if system_prompt:
            payload["system_prompt"] = system_prompt
        result = await _fal.run_async("openrouter/router", arguments=payload)
        output = result.get("output", "")
        if not output:
            raise RuntimeError(
                f"any_llm_completion({model}) returned no output (raw: {result!r})"
            )
        return output

    async def analyze_image(
        self,
        image_urls: list[str],
        prompt: str,
        model: str = "anthropic/claude-sonnet-4.6",
    ) -> str:
        result = await _fal.run_async(
            "openrouter/router/vision",
            arguments={
                "image_urls": image_urls,
                "prompt": prompt,
                "model": model,
            },
        )
        output = result.get("output", "")
        if not output:
            raise RuntimeError(
                f"analyze_image({model}) returned no output (raw: {result!r})"
            )
        return output

    async def analyze_video(
        self,
        video_urls: list[str],
        prompt: str,
        model: str = "anthropic/claude-sonnet-4.6",
    ) -> str:
        result = await _fal.run_async(
            "openrouter/router/video/enterprise",
            arguments={
                "video_urls": video_urls,
                "prompt": prompt,
                "model": model,
            },
        )
        output = result.get("output", "")
        if not output:
            raise RuntimeError(
                f"analyze_video({model}) returned no output (raw: {result!r})"
            )
        return output

    # ── 3D ─────────────────────────────────────────────────────────────
    async def generate_3d_from_text(
        self,
        prompt: str,
        generate_type: str = "Normal",
        enable_pbr: bool = False,
        model: str = "fal-ai/hunyuan3d-v3/text-to-3d",
    ) -> dict[str, str]:
        result = await _fal.run_async(
            model,
            arguments={
                "prompt": prompt,
                "generate_type": generate_type,
                "enable_pbr": enable_pbr,
            },
        )
        urls = {
            "glb_url": (result.get("model_glb") or {}).get("url", ""),
            "thumbnail_url": (result.get("thumbnail") or {}).get("url", ""),
        }
        if not urls["glb_url"]:
            raise RuntimeError(
                f"generate_3d_from_text({model}) returned no GLB (raw: {result!r})"
            )
        return urls

    async def generate_3d_from_images(
        self,
        request: ImageTo3DRequest,
        model: str = "fal-ai/meshy/v5/multi-image-to-3d",
    ) -> dict[str, str]:
        arguments: dict[str, Any] = {"image_url": request.image_url}
        if request.left_image_url:
            arguments["left_image_url"] = request.left_image_url
        if request.back_image_url:
            arguments["back_image_url"] = request.back_image_url
        if request.right_image_url:
            arguments["right_image_url"] = request.right_image_url
        result = await _fal.run_async(model, arguments=arguments)
        urls = {
            "model_url": (result.get("model_mesh") or {}).get("url", ""),
            "thumbnail_url": (result.get("thumbnail") or {}).get("url", ""),
        }
        if not urls["model_url"]:
            raise RuntimeError(
                f"generate_3d_from_images({model}) returned no mesh (raw: {result!r})"
            )
        return urls

    async def remesh_3d_model(
        self,
        model_url: str,
        target_count: int = 50000,
        model: str = "fal-ai/meshy/v5/remesh",
    ) -> str:
        result = await _fal.run_async(
            model,
            arguments={"model_url": model_url, "target_count": target_count},
        )
        url = (result.get("model_mesh") or {}).get("url", "")
        return _require(url, f"remesh_3d_model({model})", result)

    async def retexture_3d_model(
        self,
        model_url: str,
        object_prompt: str,
        style_prompt: str = "",
        model: str = "fal-ai/meshy/v5/retexture",
    ) -> str:
        arguments: dict[str, Any] = {
            "model_url": model_url,
            "object_prompt": object_prompt,
        }
        if style_prompt:
            arguments["style_prompt"] = style_prompt
        result = await _fal.run_async(model, arguments=arguments)
        url = (result.get("model_mesh") or {}).get("url", "")
        return _require(url, f"retexture_3d_model({model})", result)

    async def generate_human_motion(
        self, prompt: str, model: str = "fal-ai/hunyuan-motion/fast"
    ) -> str:
        result = await _fal.run_async(model, arguments={"prompt": prompt})
        url = (result.get("video") or {}).get("url", "")
        return _require(url, f"generate_human_motion({model})", result)

    # ── Training ───────────────────────────────────────────────────────
    async def train_flux_lora(
        self,
        images_data_url: str,
        trigger_word: str = "",
        steps: int = 1000,
        is_style: bool = False,
        model: str = "fal-ai/flux-lora-fast-training",
    ) -> dict[str, str]:
        """Train a FLUX LoRA. `images_data_url` is a zip of training images.

        Returns `{lora_url, config_url}`. Cost: ~$2/training on the fast
        trainer. Expect several minutes of queue time; the orchestrator
        blocks until done.
        """
        arguments: dict[str, Any] = {
            "images_data_url": images_data_url,
            "steps": steps,
            "is_style": is_style,
        }
        if trigger_word:
            arguments["trigger_word"] = trigger_word
        result = await _fal.run_async(model, arguments=arguments)
        urls = {
            "lora_url": (result.get("diffusers_lora_file") or {}).get("url", ""),
            "config_url": (result.get("config_file") or {}).get("url", ""),
        }
        if not urls["lora_url"]:
            raise RuntimeError(
                f"train_flux_lora({model}) returned no LoRA (raw: {result!r})"
            )
        return urls


fal_client = FalClient()
