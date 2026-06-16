# src/media_agents/agents/specialist/registry.py
from __future__ import annotations
from pydantic_ai import Agent
from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.specialist.chat_openai import chat_openai_agent
from media_agents.agents.specialist.any_llm import any_llm_agent
from media_agents.agents.specialist.vision import vision_agent
from media_agents.agents.specialist.video_analysis import video_analysis_agent
from media_agents.agents.specialist.music import music_agent
from media_agents.agents.specialist.text_to_3d import text_to_3d_agent
from media_agents.agents.specialist.image_to_3d import image_to_3d_agent
from media_agents.agents.specialist.remesh_3d import remesh_3d_agent
from media_agents.agents.specialist.retexture_3d import retexture_3d_agent
from media_agents.agents.specialist.human_motion import human_motion_agent
from media_agents.agents.specialist.text_to_image import text_to_image_agent
from media_agents.agents.specialist.image_to_image import image_to_image_agent
from media_agents.agents.specialist.text_to_video import text_to_video_agent
from media_agents.agents.specialist.image_to_video import image_to_video_agent
from media_agents.agents.specialist.video_to_video import video_to_video_agent
from media_agents.agents.specialist.text_to_speech import text_to_speech_agent
from media_agents.agents.specialist.speech_to_text import speech_to_text_agent
from media_agents.agents.specialist.audio_to_audio import audio_to_audio_agent
from media_agents.agents.specialist.audio_to_video import audio_to_video_agent
from media_agents.agents.specialist.video_to_audio import video_to_audio_agent
from media_agents.agents.specialist.speech_to_speech import speech_to_speech_agent
from media_agents.agents.specialist.training import training_agent
from media_agents.agents.specialist.structured_output import structured_output_agent

SPECIALIST_REGISTRY: dict[str, Agent[OrchestratorDeps, str]] = {
    "openrouter_chat": chat_openai_agent,
    "any_llm": any_llm_agent,
    "vision": vision_agent,
    "video_analysis": video_analysis_agent,
    "music_generation": music_agent,
    "text_to_3d": text_to_3d_agent,
    "image_to_3d": image_to_3d_agent,
    "remesh_3d": remesh_3d_agent,
    "retexture_3d": retexture_3d_agent,
    "human_motion": human_motion_agent,
    "text_to_image": text_to_image_agent,
    "image_to_image": image_to_image_agent,
    "text_to_video": text_to_video_agent,
    "image_to_video": image_to_video_agent,
    "video_to_video": video_to_video_agent,
    "text_to_speech": text_to_speech_agent,
    "speech_to_text": speech_to_text_agent,
    "audio_to_audio": audio_to_audio_agent,
    "audio_to_video": audio_to_video_agent,
    "video_to_audio": video_to_audio_agent,
    "speech_to_speech": speech_to_speech_agent,
    "training": training_agent,
    "structured_output": structured_output_agent,
    # Back-compat aliases for pre-existing agents saved before the capability
    # rename (Image Generator used "image", Video Creator used "video").
    "image": text_to_image_agent,
    "video": text_to_video_agent,
}
