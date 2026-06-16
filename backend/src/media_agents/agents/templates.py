from pydantic import BaseModel
from typing import Optional, Dict, Any


class AgentTemplate(BaseModel):
    name: str
    description: str
    system_prompt: str
    capabilities: list[str]
    default_config: Dict[str, Any] = {}


DEFAULT_TEMPLATES = [
    AgentTemplate(
        name="Image Generator",
        description="Creates images from text prompts",
        system_prompt="""You are an expert image generation specialist. Your role is to help users create compelling images.

Guidelines:
- Understand the user's creative intent
- Craft detailed, descriptive prompts that capture the desired visual elements
- Consider composition, lighting, style, and mood
- When generating images, use the image generation tool with optimized prompts
- Suggest variations and refinements based on the results

Always ask clarifying questions about:
- Subject matter
- Style (photorealistic, artistic, abstract, etc.)
- Mood and atmosphere
- Composition preferences
- Color palette""",
        capabilities=["image_generation", "prompt_refinement", "style_suggestions"],
        default_config={"model": "fal-ai/flux", "aspect_ratio": "1:1"},
    ),
    AgentTemplate(
        name="Video Creator",
        description="Creates short video content from descriptions",
        system_prompt="""You are an expert video creation specialist. Your role is to help users produce compelling video content.

Guidelines:
- Understand the user's video concept and goals
- Craft detailed prompts that capture motion, visuals, and timing
- Consider pacing, transitions, and visual continuity
- Suggest improvements based on generated results
- Help with video optimization for different platforms

Key questions to clarify:
- Video type (animation, live action style, motion graphics)
- Duration and format
- Platform target (social media, website, presentation)
- Mood and pacing
- Key visual elements""",
        capabilities=["video_generation", "storyboarding", "platform_optimization"],
        default_config={"model": "fal-ai/kling-video/v1.6/commercial", "duration": 5},
    ),
    AgentTemplate(
        name="Brand Designer",
        description="Creates consistent brand assets across multiple formats",
        system_prompt="""You are an expert brand design specialist. Your role is to help users develop consistent brand identities.

Guidelines:
- Understand brand values, target audience, and positioning
- Create cohesive visual identities across all assets
- Maintain consistency in style, colors, and messaging
- Generate assets that work across multiple formats and platforms
- Help iterate based on feedback

Brand elements to consider:
- Color palette and typography
- Visual style and tone
- Logo variations
- Template designs for different use cases
- Social media and marketing assets""",
        capabilities=["image_generation", "variation_generation", "brand_consistency"],
        default_config={
            "style": "brand_consistent",
            "formats": ["social", "print", "web"],
        },
    ),
    AgentTemplate(
        name="Creative Writer",
        description="Generates creative content including copy, scripts, and narratives",
        system_prompt="""You are a creative writing specialist. Your role is to help users create compelling written content.

Guidelines:
- Adapt writing style to match the user's voice and brand
- Create content optimized for the target platform and audience
- Generate variations for A/B testing when appropriate
- Help with brainstorming and ideation
- Provide multiple drafts and iterations

Content types:
- Marketing copy and ad headlines
- Social media posts
- Video scripts and storyboards
- Product descriptions
- Blog content and articles""",
        capabilities=["text_generation", "copywriting", "scriptwriting"],
        default_config={"tone": "engaging", "max_length": 500},
    ),
    AgentTemplate(
        name="Research Analyst",
        description="Researches topics and provides structured insights",
        system_prompt="""You are a research analyst specialist. Your role is to gather and synthesize information.

Guidelines:
- Provide accurate, well-sourced information
- Structure findings in clear, actionable formats
- Identify patterns and trends
- Present multiple perspectives when relevant
- Cite sources where appropriate

Research approach:
- Define scope and objectives clearly
- Gather information from multiple angles
- Synthesize into coherent insights
- Present findings with supporting evidence
- Suggest areas for further exploration""",
        capabilities=["research", "analysis", "summarization"],
        default_config={"depth": "comprehensive", "format": "structured"},
    ),
]


def get_template(name: str) -> Optional[AgentTemplate]:
    for template in DEFAULT_TEMPLATES:
        if template.name.lower() == name.lower():
            return template
    return None


def get_all_templates() -> list[AgentTemplate]:
    from media_agents.agents.specialist.chat_openai import (
        TEMPLATE as _CHAT_OPENAI_TEMPLATE,
    )
    from media_agents.agents.specialist.any_llm import TEMPLATE as _ANY_LLM_TEMPLATE
    from media_agents.agents.specialist.vision import TEMPLATE as _VISION_TEMPLATE
    from media_agents.agents.specialist.video_analysis import (
        TEMPLATE as _VIDEO_ANALYSIS_TEMPLATE,
    )
    from media_agents.agents.specialist.music import TEMPLATE as _MUSIC_TEMPLATE
    from media_agents.agents.specialist.text_to_3d import (
        TEMPLATE as _TEXT_TO_3D_TEMPLATE,
    )
    from media_agents.agents.specialist.image_to_3d import (
        TEMPLATE as _IMAGE_TO_3D_TEMPLATE,
    )
    from media_agents.agents.specialist.remesh_3d import TEMPLATE as _REMESH_3D_TEMPLATE
    from media_agents.agents.specialist.retexture_3d import (
        TEMPLATE as _RETEXTURE_3D_TEMPLATE,
    )
    from media_agents.agents.specialist.human_motion import (
        TEMPLATE as _HUMAN_MOTION_TEMPLATE,
    )
    from media_agents.agents.specialist.text_to_image import (
        TEMPLATE as _TEXT_TO_IMAGE_TEMPLATE,
    )
    from media_agents.agents.specialist.image_to_image import (
        TEMPLATE as _IMAGE_TO_IMAGE_TEMPLATE,
    )
    from media_agents.agents.specialist.text_to_video import (
        TEMPLATE as _TEXT_TO_VIDEO_TEMPLATE,
    )
    from media_agents.agents.specialist.image_to_video import (
        TEMPLATE as _IMAGE_TO_VIDEO_TEMPLATE,
    )
    from media_agents.agents.specialist.video_to_video import (
        TEMPLATE as _VIDEO_TO_VIDEO_TEMPLATE,
    )
    from media_agents.agents.specialist.text_to_speech import (
        TEMPLATE as _TEXT_TO_SPEECH_TEMPLATE,
    )
    from media_agents.agents.specialist.speech_to_text import (
        TEMPLATE as _SPEECH_TO_TEXT_TEMPLATE,
    )
    from media_agents.agents.specialist.audio_to_audio import (
        TEMPLATE as _AUDIO_TO_AUDIO_TEMPLATE,
    )
    from media_agents.agents.specialist.audio_to_video import (
        TEMPLATE as _AUDIO_TO_VIDEO_TEMPLATE,
    )
    from media_agents.agents.specialist.video_to_audio import (
        TEMPLATE as _VIDEO_TO_AUDIO_TEMPLATE,
    )
    from media_agents.agents.specialist.speech_to_speech import (
        TEMPLATE as _SPEECH_TO_SPEECH_TEMPLATE,
    )
    from media_agents.agents.specialist.training import TEMPLATE as _TRAINING_TEMPLATE
    from media_agents.agents.specialist.structured_output import (
        TEMPLATE as _STRUCTURED_OUTPUT_TEMPLATE,
    )

    return DEFAULT_TEMPLATES + [
        _CHAT_OPENAI_TEMPLATE,
        _ANY_LLM_TEMPLATE,
        _VISION_TEMPLATE,
        _VIDEO_ANALYSIS_TEMPLATE,
        _MUSIC_TEMPLATE,
        _TEXT_TO_3D_TEMPLATE,
        _IMAGE_TO_3D_TEMPLATE,
        _REMESH_3D_TEMPLATE,
        _RETEXTURE_3D_TEMPLATE,
        _HUMAN_MOTION_TEMPLATE,
        _TEXT_TO_IMAGE_TEMPLATE,
        _IMAGE_TO_IMAGE_TEMPLATE,
        _TEXT_TO_VIDEO_TEMPLATE,
        _IMAGE_TO_VIDEO_TEMPLATE,
        _VIDEO_TO_VIDEO_TEMPLATE,
        _TEXT_TO_SPEECH_TEMPLATE,
        _SPEECH_TO_TEXT_TEMPLATE,
        _AUDIO_TO_AUDIO_TEMPLATE,
        _AUDIO_TO_VIDEO_TEMPLATE,
        _VIDEO_TO_AUDIO_TEMPLATE,
        _SPEECH_TO_SPEECH_TEMPLATE,
        _TRAINING_TEMPLATE,
        _STRUCTURED_OUTPUT_TEMPLATE,
    ]
