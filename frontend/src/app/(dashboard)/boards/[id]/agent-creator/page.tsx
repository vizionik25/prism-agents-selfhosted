"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useParams } from "next/navigation"
import Link from "next/link"
import {
  ArrowLeft,
  Plus,
  Wand2,
  Trash2,
  Play,
  Users,
  Sparkles,
  Layers,
  Search,
  Cpu,
  X,
  Check,
  Pencil,
  Radar,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useAgentStore, useTeamStore } from "@/stores"
import { api, type Agent, type Team } from "@/lib/api"
import { cn } from "@/lib/utils"

type ModelChoice = { label: string; value: string }

interface Template {
  name: string
  description: string
  icon: string
  category: "Media" | "Audio" | "3D" | "AI" | "Creative" | "Training"
  defaultPrompt: string
  capability?: string
  defaultModel?: string
  modelChoices?: ModelChoice[]
}

const TEMPLATES: Template[] = [
  // ── Media ────────────────────────────────────────────────
  {
    name: "Text to Image",
    description: "Generate images from text prompts (FLUX / Ideogram / SD family)",
    icon: "🎨",
    category: "Media",
    capability: "text_to_image",
    defaultModel: "fal-ai/flux/schnell",
    modelChoices: [
      { label: "Flux Schnell (fast, ~$0.003/MP)", value: "fal-ai/flux/schnell" },
      { label: "Flux Dev (quality, ~$0.025/MP)", value: "fal-ai/flux/dev" },
      { label: "Flux Pro v1.1 (max fidelity)", value: "fal-ai/flux-pro/v1.1" },
      { label: "Ideogram v3 (text in images)", value: "fal-ai/ideogram/v3" },
      { label: "Nano Banana (prompt adherence)", value: "fal-ai/nano-banana" },
    ],
    defaultPrompt:
      "You are a text-to-image specialist. Craft detailed prompts covering subject, composition, lighting, style, mood, and color palette. Default cost ~$0.003/megapixel on Flux Schnell.",
  },
  {
    name: "Image Editor",
    description: "Edit existing images with natural language (Nano Banana)",
    icon: "🖌️",
    category: "Media",
    capability: "image_to_image",
    defaultModel: "fal-ai/nano-banana/edit",
    modelChoices: [
      { label: "Nano Banana Edit ($0.039/image)", value: "fal-ai/nano-banana/edit" },
      { label: "Flux 2 Flash ($0.005/MP, cheap)", value: "fal-ai/flux-2/flash/edit" },
      { label: "GPT Image 1 Edit ($0.002)", value: "fal-ai/gpt-image-1/edit-image" },
      { label: "Flux Kontext Dev", value: "fal-ai/flux-kontext/dev" },
      { label: "ESRGAN (pure upscale)", value: "fal-ai/esrgan" },
    ],
    defaultPrompt:
      "You are an image-editing specialist. Given one or more image URLs and a clear instruction (swap, restyle, retouch, upscale), call edit_image with the URLs and the instruction.",
  },
  {
    name: "Text to Video",
    description: "Generate short video clips from text (Kling / Veo / LTX)",
    icon: "🎬",
    category: "Media",
    capability: "text_to_video",
    defaultModel: "fal-ai/kling-video/v1.6/standard/text-to-video",
    modelChoices: [
      { label: "Kling 1.6 Standard (balanced)", value: "fal-ai/kling-video/v1.6/standard/text-to-video" },
      { label: "Luma Ray 2 Flash (fast, cheap)", value: "fal-ai/luma-dream-machine/ray-2-flash" },
      { label: "Veo 3.1 (high quality)", value: "fal-ai/veo3.1" },
      { label: "Kling 2 (newer, slower)", value: "fal-ai/kling-video/v2" },
    ],
    defaultPrompt:
      "You are a text-to-video specialist. Prompts should cover motion, camera movement, subject, environment, lighting, and pacing. Warn the user that generation blocks for 30s-2min.",
  },
  {
    name: "Image to Video",
    description: "Animate a still image with a motion prompt",
    icon: "🖼️",
    category: "Media",
    capability: "image_to_video",
    defaultModel: "fal-ai/kling-video/v1.6/standard/image-to-video",
    modelChoices: [
      { label: "Kling 1.6 Std i2v", value: "fal-ai/kling-video/v1.6/standard/image-to-video" },
      { label: "Kling 2.6 Std i2v (newer)", value: "fal-ai/kling-video/v2.6/standard/image-to-video" },
      { label: "Luma Ray i2v", value: "fal-ai/luma-dream-machine/ray-2-flash/image-to-video" },
    ],
    defaultPrompt:
      "You are an image-to-video specialist. Animate a still image — describe camera movement + subject motion + mood. Duration is '5' or '10' seconds.",
  },
  {
    name: "Lipsync Video",
    description: "Sync lips in a video to a new audio track (LatentSync)",
    icon: "💋",
    category: "Media",
    capability: "video_to_video",
    defaultModel: "fal-ai/latentsync",
    modelChoices: [
      { label: "LatentSync ($0.005/sec)", value: "fal-ai/latentsync" },
      { label: "Sync Lipsync v2 ($3/min, higher quality)", value: "fal-ai/sync-lipsync/v2" },
      { label: "Pixverse Lipsync ($0.04)", value: "fal-ai/pixverse/lipsync" },
    ],
    defaultPrompt:
      "You are a video-to-video lipsync specialist. Given a video URL and an audio URL, return a video whose lip movements match the new audio.",
  },
  // ── Audio ────────────────────────────────────────────────
  {
    name: "Music Generator",
    description: "Create complete music tracks with vocals and full arrangements",
    icon: "🎵",
    category: "Audio",
    capability: "music_generation",
    defaultModel: "fal-ai/minimax-music/v2.6",
    defaultPrompt:
      "You are a music generation specialist powered by MiniMax Music 2.6. Produce fully-arranged music from style descriptions and optional lyrics using [Intro]/[Verse]/[Chorus] tags.",
  },
  {
    name: "Text to Speech",
    description: "Natural-sounding speech synthesis (MiniMax Speech-02)",
    icon: "🗣️",
    category: "Audio",
    capability: "text_to_speech",
    defaultModel: "fal-ai/minimax/speech-02-turbo",
    modelChoices: [
      { label: "MiniMax Speech-02 Turbo ($0.06)", value: "fal-ai/minimax/speech-02-turbo" },
      { label: "MiniMax Speech-02 HD ($0.10)", value: "fal-ai/minimax/speech-02-hd" },
      { label: "Inworld TTS-1.5 Max ($0.01)", value: "fal-ai/inworld-tts" },
      { label: "VibeVoice 1.5B ($0.04)", value: "fal-ai/vibevoice" },
    ],
    defaultPrompt:
      "You are a text-to-speech specialist. Call generate_speech with the text the user wants spoken. Voice presets: 'Wise_Woman', 'Deep_Voice_Man', 'Friendly_Person'. Max 5000 chars.",
  },
  {
    name: "Audio Transcription",
    description: "Transcribe or translate audio to text (Whisper)",
    icon: "📝",
    category: "Audio",
    capability: "speech_to_text",
    defaultModel: "fal-ai/whisper",
    modelChoices: [
      { label: "Whisper", value: "fal-ai/whisper" },
      { label: "Wizper (fal-optimized v3)", value: "fal-ai/wizper" },
      { label: "ElevenLabs Scribe V2 ($0.008)", value: "fal-ai/elevenlabs/speech-to-text/scribe-v2" },
    ],
    defaultPrompt:
      "You are an audio transcription specialist powered by Whisper. task='transcribe' or 'translate' (to English). Leave language=None for auto-detection.",
  },
  {
    name: "Stem Separator",
    description: "Split a song into vocals, drums, bass, and other stems (Demucs)",
    icon: "🎛️",
    category: "Audio",
    capability: "audio_to_audio",
    defaultModel: "fal-ai/demucs",
    modelChoices: [
      { label: "Demucs (free, 6-stem)", value: "fal-ai/demucs" },
      { label: "ElevenLabs Audio Isolation", value: "fal-ai/elevenlabs/audio-isolation" },
      { label: "Sam Audio separate ($0.05)", value: "fal-ai/sam-audio/separate" },
    ],
    defaultPrompt:
      "You are an audio stem-separation specialist. Default Demucs 6-stem model returns vocals, drums, bass, guitar, piano, and other.",
  },
  {
    name: "Talking Avatar",
    description: "Lip-synced avatar video from image + audio",
    icon: "🎭",
    category: "Audio",
    capability: "audio_to_video",
    defaultModel: "fal-ai/stable-avatar",
    modelChoices: [
      { label: "Stable Avatar ($0.10)", value: "fal-ai/stable-avatar" },
      { label: "EchoMimic v3 ($0.20)", value: "fal-ai/echomimic-v3" },
      { label: "LongCat Single Avatar ($0.30)", value: "fal-ai/longcat-single-avatar/image-audio-to-video" },
    ],
    defaultPrompt:
      "You are a talking-avatar specialist powered by Stable Avatar. Image + audio + demeanor prompt → video of the character speaking. Up to 5 minutes long.",
  },
  {
    name: "Foley / Soundtrack",
    description: "Generate a synced soundtrack for a silent video",
    icon: "🔊",
    category: "Audio",
    capability: "video_to_audio",
    defaultModel: "fal-ai/kling-video/video-to-audio",
    modelChoices: [
      { label: "Kling Video-to-Audio ($0.035)", value: "fal-ai/kling-video/video-to-audio" },
      { label: "Mirelo SFX v1 ($0.007/sec)", value: "mirelo-ai/sfx-v1/video-to-audio" },
      { label: "Mirelo SFX v1.5", value: "mirelo-ai/sfx-v1.5/video-to-audio" },
    ],
    defaultPrompt:
      "You are a video-to-audio Foley specialist. Video 3-20s, <100MB. Prompts are capped at 200 chars. Returns BOTH dubbed video and raw audio track.",
  },
  {
    name: "Voice Converter",
    description: "Convert audio from one voice to another (Chatterbox)",
    icon: "🎙️",
    category: "Audio",
    capability: "speech_to_speech",
    defaultModel: "fal-ai/chatterbox/speech-to-speech",
    modelChoices: [
      { label: "Chatterbox S2S", value: "fal-ai/chatterbox/speech-to-speech" },
      { label: "ChatterboxHD S2S", value: "resemble-ai/chatterboxhd/speech-to-speech" },
    ],
    defaultPrompt:
      "You are a voice-conversion specialist. Source audio URL (speech to convert) + optional target voice URL (reference to match).",
  },
  {
    name: "Human Motion",
    description: "Generates 3D human motion sequences from text descriptions",
    icon: "🏃",
    category: "3D",
    capability: "human_motion",
    defaultModel: "fal-ai/hunyuan-motion/fast",
    defaultPrompt:
      "You are a 3D human motion generation specialist. Generate realistic motion sequences from natural language descriptions of movements.",
  },
  // ── 3D ───────────────────────────────────────────────────
  {
    name: "Text to 3D",
    description: "Generates 3D models from text descriptions",
    icon: "🧊",
    category: "3D",
    capability: "text_to_3d",
    defaultModel: "fal-ai/hunyuan3d-v3/text-to-3d",
    defaultPrompt:
      "You are a 3D model generation specialist. Create detailed 3D models from text descriptions using Hunyuan3D.",
  },
  {
    name: "Image to 3D",
    description: "Converts images into 3D models",
    icon: "📷",
    category: "3D",
    capability: "image_to_3d",
    defaultModel: "fal-ai/meshy/v5/multi-image-to-3d",
    defaultPrompt:
      "You are a 3D reconstruction specialist. Convert images into detailed 3D models using Meshy.",
  },
  {
    name: "Remesh 3D",
    description: "Optimizes the polygon count of 3D models",
    icon: "🔺",
    category: "3D",
    capability: "remesh_3d",
    defaultModel: "fal-ai/meshy/v5/remesh",
    defaultPrompt:
      "You are a 3D mesh optimization specialist. Remesh 3D models to optimize polygon count for different use cases.",
  },
  {
    name: "Retexture 3D",
    description: "Applies new textures to existing 3D models",
    icon: "🖌️",
    category: "3D",
    capability: "retexture_3d",
    defaultModel: "fal-ai/meshy/v5/retexture",
    defaultPrompt:
      "You are a 3D texturing specialist. Apply new textures and materials to existing 3D models based on style descriptions.",
  },
  // ── AI ───────────────────────────────────────────────────
  {
    name: "Vision Analyst",
    description: "Analyzes images — captioning, OCR, visual Q&A",
    icon: "👁️",
    category: "AI",
    capability: "vision",
    defaultModel: "anthropic/claude-sonnet-4.6",
    modelChoices: [
      { label: "Claude Sonnet 4.6", value: "anthropic/claude-sonnet-4.6" },
      { label: "GPT-4o", value: "openai/gpt-4o" },
      { label: "Llama 4 Maverick", value: "meta-llama/llama-4-maverick" },
    ],
    defaultPrompt:
      "You are a visual analysis specialist. Analyze images to answer questions, caption, OCR, or describe scenes.",
  },
  {
    name: "Video Analyst",
    description: "Analyzes video content — transcription, scene description, Q&A",
    icon: "🎥",
    category: "AI",
    capability: "video_analysis",
    defaultModel: "anthropic/claude-sonnet-4.6",
    modelChoices: [
      { label: "Claude Sonnet 4.6", value: "anthropic/claude-sonnet-4.6" },
      { label: "GPT-4o", value: "openai/gpt-4o" },
      { label: "Llama 4 Maverick", value: "meta-llama/llama-4-maverick" },
    ],
    defaultPrompt:
      "You are a video analysis specialist. Process video files for transcription, description, or Q&A.",
  },
  {
    name: "Structured Output",
    description: "Extract JSON from prompts or images — describe the schema",
    icon: "📋",
    category: "AI",
    capability: "structured_output",
    defaultModel: "anthropic/claude-sonnet-4.6",
    modelChoices: [
      { label: "Claude Sonnet 4.6", value: "anthropic/claude-sonnet-4.6" },
      { label: "GPT-4o", value: "openai/gpt-4o" },
      { label: "Gemini 2.5 Flash", value: "google/gemini-2.5-flash" },
    ],
    defaultPrompt:
      "You are a structured-output specialist. Describe a JSON schema and provide raw text or image URLs; the agent returns strictly valid JSON (no markdown fences).",
  },
  // ── Training ─────────────────────────────────────────────
  {
    name: "LoRA Trainer",
    description: "Train a custom FLUX LoRA on your own images (subjects, styles)",
    icon: "🏋️",
    category: "Training",
    capability: "training",
    defaultModel: "fal-ai/flux-lora-fast-training",
    modelChoices: [
      { label: "FLUX LoRA Fast Training (~$2)", value: "fal-ai/flux-lora-fast-training" },
      { label: "FLUX LoRA Portrait Trainer ($0.0024)", value: "fal-ai/flux-lora-portrait-trainer" },
      { label: "FLUX Kontext Trainer ($2.5)", value: "fal-ai/flux-kontext-trainer" },
      { label: "Turbo FLUX Trainer ($2.40)", value: "fal-ai/turbo-flux-trainer" },
    ],
    defaultPrompt:
      "You are a LoRA-training specialist. Provide a ZIP URL of training images (4+ images ideal, 10-30 for best quality), a trigger_word, and whether it's a style or subject. WARN about the ~$2 cost before launching.",
  },
  // ── Creative ─────────────────────────────────────────────
  {
    name: "Brand Designer",
    description: "Creates consistent brand assets",
    icon: "✨",
    category: "Creative",
    defaultPrompt:
      "You are an expert brand design specialist. Create cohesive visual identities across all assets while maintaining brand consistency.",
  },
  {
    name: "Creative Writer",
    description: "Generates creative content and copy",
    icon: "✍️",
    category: "Creative",
    defaultPrompt:
      "You are a creative writing specialist. Help users create compelling written content adapted to their voice and brand.",
  },
  {
    name: "Research Analyst",
    description: "Researches and provides insights",
    icon: "🔍",
    category: "Creative",
    defaultPrompt:
      "You are a research analyst. Gather and synthesize information, identify patterns, and present structured findings.",
  },
]

const TEMPLATES_BY_CAPABILITY = new Map(TEMPLATES.filter((t) => t.capability).map((t) => [t.capability, t]))

const CATEGORIES = ["All", "Media", "Audio", "3D", "AI", "Creative", "Training", "Custom"] as const
type Category = (typeof CATEGORIES)[number]

type TabKey = "creator" | "agents" | "teams"

const TABS: { key: TabKey; label: string; icon: typeof Wand2 }[] = [
  { key: "creator", label: "Creator", icon: Wand2 },
  { key: "agents", label: "Agents", icon: Layers },
  { key: "teams", label: "Teams", icon: Users },
]

const ROUTING_STRATEGIES = [
  { value: "llm_routed", label: "LLM Routed", hint: "Orchestrator picks the member" },
  { value: "capability_match", label: "Capability Match", hint: "Match by tool type" },
  { value: "round_robin", label: "Round Robin", hint: "Rotate through members" },
] as const

const DEFAULT_ORCHESTRATOR_MODELS = [
  "anthropic/claude-sonnet-4.6",
  "openai/gpt-4o",
  "google/gemini-2.5-flash",
  "meta-llama/llama-4-maverick",
]

const DEFAULT_ORCHESTRATOR_PROMPT =
  "You are a team orchestrator. Analyze user requests, break them into steps, and delegate to the most suitable team member. Synthesize results into a cohesive response."

interface TeamTemplate {
  slug: string
  name: string
  tagline: string
  description: string
  accent: string // emoji
  capabilities: string[]
  agent_ids?: string[]
  orchestrator: {
    system_prompt: string
    model: string
    temperature: number
    routing_strategy: string
  }
}

const TEAM_TEMPLATES: TeamTemplate[] = [
  {
    slug: "world-builder",
    name: "3D World Forge",
    tagline: "Concept-to-asset pipeline for video game worlds",
    description:
      "Drives a complete 3D pipeline — concept art, mesh generation, polycount optimization, texturing, and character motion — for game environments and characters.",
    accent: "🌐",
    capabilities: [
      "text_to_image",
      "text_to_3d",
      "image_to_3d",
      "remesh_3d",
      "retexture_3d",
      "human_motion",
    ],
    orchestrator: {
      system_prompt: `You are a 3D world-building director. Coordinate this asset pipeline:

PHASE 1 — CONCEPT
• Use the text-to-image specialist to generate 2-4 reference frames per asset (front / side / detail). Lock a consistent visual language up front (style, palette, lighting).

PHASE 2 — MESH GENERATION
• For descriptive prompts only → text-to-3d (Hunyuan3D).
• When concept art exists → image-to-3d (Meshy) using the strongest reference frame for higher fidelity.

PHASE 3 — OPTIMIZATION
• Pipe every mesh through remesh-3d. Default targets:
  – Mobile / VR: ≤ 5k tris
  – Real-time PC / console: 10-30k tris
  – Cinematic / hero asset: 80-200k tris
• Always confirm the target platform with the user before committing budgets.

PHASE 4 — MATERIALS
• Use retexture-3d to apply matching PBR materials across the asset set so nothing looks orphaned.

PHASE 5 — CHARACTERS
• For any humanoid asset, use human-motion to generate a base idle + 1-2 signature motions (walk, attack, gesture).

OUTPUT
Return a structured asset manifest: { asset_name, mesh_url, texture_url, motion_url?, tri_count, platform_target }. Flag any asset you'd recommend regenerating and why.`,
      model: "anthropic/claude-sonnet-4.6",
      temperature: 0.4,
      routing_strategy: "capability_match",
    },
  },
  {
    slug: "campaign-studio",
    name: "Campaign Studio",
    tagline: "Research → still ads → video ads → audio, end-to-end",
    description:
      "Runs a full marketing campaign from competitive research and brand brief through still ads, animated ads, voiceover, and a custom backing track.",
    accent: "📣",
    capabilities: [
      "vision",
      "structured_output",
      "text_to_image",
      "image_to_image",
      "text_to_video",
      "image_to_video",
      "text_to_speech",
      "music_generation",
      "video_to_audio",
    ],
    orchestrator: {
      system_prompt: `You are a marketing campaign director. Run this 5-phase workflow and only advance phases when the prior outputs are user-approved.

PHASE 1 — RESEARCH & BRIEF
• Use vision to analyze any competitor screenshots, mood boards, or existing brand assets the user shares.
• Use structured-output to extract a Brand Brief JSON: { positioning, tone, palette: hex[], type_personality, target_persona, do_nots[], hero_message }.
• Present the brief and ask for approval before continuing.

PHASE 2 — STILL CONCEPTS (3-5 routes)
• Generate 3-5 distinct creative routes via text-to-image. Reuse the same prompt skeleton across routes — only vary the concept descriptor — so palette/type stay consistent.
• Render each route in 2 sizes: 1:1 (social) and 16:9 (display).

PHASE 3 — REFINEMENT
• Once the user picks a route, use image-to-image (Nano Banana Edit) to:
  – Drop in the user's logo / wordmark
  – Color-grade to brand palette
  – Reframe for additional aspect ratios (9:16 story, 4:5 feed)

PHASE 4 — MOTION
• Animate the chosen still via image-to-video (Kling i2v, 5s) for short-form social.
• For long-form spots, use text-to-video (Kling Standard, 10s) with prompts derived from the brief.

PHASE 5 — AUDIO BED
• Generate a voiceover line via text-to-speech matching the brand tone (Wise_Woman / Friendly_Person / Deep_Voice_Man).
• Generate a 15-30s instrumental backing track via music-generation that matches the brand mood (e.g. "warm acoustic, hopeful, mid-tempo").
• If video has critical visual events (door slam, product reveal), use video-to-audio for synced foley.

DELIVERABLE
A campaign tree: { brief, still_concepts[], chosen_route, refined_stills[], video_assets[], voiceover_url, music_url, recommended_pairings[] }. Always tell the user the rough credit cost before launching the motion phase.`,
      model: "anthropic/claude-sonnet-4.6",
      temperature: 0.7,
      routing_strategy: "llm_routed",
    },
  },
  {
    slug: "cover-band",
    name: "AI Cover Band",
    tagline: "Cover track, vocals, album art, full music video",
    description:
      "Produces an AI cover song end-to-end — instrumental arrangement, vocal performance, album art, and a lip-synced music video with b-roll.",
    accent: "🎤",
    capabilities: [
      "music_generation",
      "audio_to_audio",
      "text_to_speech",
      "speech_to_speech",
      "text_to_image",
      "image_to_video",
      "audio_to_video",
      "video_to_video",
      "text_to_video",
    ],
    orchestrator: {
      system_prompt: `You are the producer of an AI cover band. Run a real recording-session flow.

STEP 1 — REFERENCE & STEMS (only if user provides a source track)
• Use audio-to-audio (Demucs) to split the original into vocals / drums / bass / other. Keep the isolated vocal as a phrasing reference.

STEP 2 — ARRANGEMENT
• Use music-generation (MiniMax) to produce a 60-90s instrumental cover in the requested style.
• Always provide structured lyrics with [Intro] / [Verse] / [Chorus] / [Bridge] / [Outro] tags and explicit instrumentation hints (e.g. "synth-pop: gated reverb drums, analog bass, glassy electric piano, no live drums").

STEP 3 — LEAD VOCAL
• Default path: text-to-speech with a tone-matched voice preset and the lyric sheet as input.
• When the user provides a reference vocal performance, use speech-to-speech (Chatterbox) to convert their singing into the chosen voice while preserving phrasing.

STEP 4 — VISUAL IDENTITY
• Use text-to-image to generate album cover + 2-3 band portrait stills. Lock the visual style across calls (one camera, one palette, one wardrobe descriptor).

STEP 5 — MUSIC VIDEO
• Lead vocalist performance: audio-to-video (Stable Avatar) using the album cover portrait + the vocal stem → lip-synced singing shots.
• Live band feel: image-to-video (Kling i2v) on each band portrait, prompting subtle performance motion (head bob, guitar strum, drum hit).
• B-roll: text-to-video for atmospheric cuts (rain on neon street, empty stage, crowd silhouette) — keep clips ≤ 5s.

STEP 6 — POLISH
• If lip sync drifts on the lead-vocal shots, run video-to-video (LatentSync) with the original vocal stem to tighten it.

DELIVERABLE
{ instrumental_url, vocal_url, mixed_track_url, album_art_url, band_stills[], music_video_url, b_roll_clips[] }. Note the total runtime spent in seconds and warn the user before any step >60s of generation time.`,
      model: "anthropic/claude-sonnet-4.6",
      temperature: 0.8,
      routing_strategy: "llm_routed",
    },
  },
]

export default function AgentCreatorPage() {
  const params = useParams()
  const boardId = params.id as string
  const { agents, setAgents, addAgent, removeAgent, updateAgent } = useAgentStore()
  const { teams, setTeams, addTeam, updateTeam, removeTeam } = useTeamStore()

  const [tab, setTab] = useState<TabKey>("creator")
  const [isLoading, setIsLoading] = useState(true)

  // Creator tab state
  const [agentName, setAgentName] = useState("")
  const [agentDescription, setAgentDescription] = useState("")
  const [systemPrompt, setSystemPrompt] = useState("")
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<string>("")
  const [editingAgentId, setEditingAgentId] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [templateCategory, setTemplateCategory] = useState<Exclude<Category, "Custom">>("All")
  const formRef = useRef<HTMLDivElement>(null)

  // Agents tab state
  const [galleryCategory, setGalleryCategory] = useState<Category>("All")
  const [searchQuery, setSearchQuery] = useState("")
  const [teamCapabilitySelection, setTeamCapabilitySelection] = useState<Set<string>>(new Set())
  const [teamAgentSelection, setTeamAgentSelection] = useState<Set<string>>(new Set())

  // Teams tab state
  const [teamDialogOpen, setTeamDialogOpen] = useState(false)
  const [editingTeam, setEditingTeam] = useState<Team | null>(null)
  const [teamName, setTeamName] = useState("")
  const [teamDescription, setTeamDescription] = useState("")
  const [teamMembers, setTeamMembers] = useState<{ capabilities: Set<string>; agentIds: Set<string> }>({
    capabilities: new Set(),
    agentIds: new Set(),
  })
  const [orchSystemPrompt, setOrchSystemPrompt] = useState(DEFAULT_ORCHESTRATOR_PROMPT)
  const [orchModel, setOrchModel] = useState(DEFAULT_ORCHESTRATOR_MODELS[0])
  const [orchTemperature, setOrchTemperature] = useState(0.7)
  const [orchRouting, setOrchRouting] = useState<string>("llm_routed")
  // Empty string = no cap. Persisted as null on the team when blank.
  const [orchMaxCredits, setOrchMaxCredits] = useState<string>("")
  const [isSavingTeam, setIsSavingTeam] = useState(false)

  useEffect(() => {
    loadData()
  }, [boardId])

  const loadData = async () => {
    setIsLoading(true)
    try {
      const [agentsRes, teamsRes] = await Promise.all([
        api.agents.list(boardId),
        api.teams.list(boardId),
      ])
      setAgents(agentsRes.agents)
      setTeams(teamsRes.teams)
    } catch (error) {
      console.error("Failed to load data:", error)
    } finally {
      setIsLoading(false)
    }
  }

  // ── Creator helpers ─────────────────────────────────────────
  const selectTemplate = (templateName: string) => {
    const template = TEMPLATES.find((t) => t.name === templateName)
    if (template) {
      setSelectedTemplate(templateName)
      setSystemPrompt(template.defaultPrompt)
      setAgentName(template.name)
      setAgentDescription(template.description)
      setSelectedModel(template.defaultModel ?? "")
      setEditingAgentId(null)
      setTab("creator")
      setTimeout(() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50)
    }
  }

  const resetForm = () => {
    setAgentName("")
    setAgentDescription("")
    setSystemPrompt("")
    setSelectedTemplate(null)
    setSelectedModel("")
    setEditingAgentId(null)
  }

  const loadAgentIntoForm = (agent: Agent) => {
    setAgentName(agent.name)
    setAgentDescription(agent.description ?? "")
    setSystemPrompt(agent.system_prompt)
    setSelectedModel((agent.config?.model as string) ?? "")
    const capability = agent.config?.capability as string | undefined
    const matchingTemplate = TEMPLATES.find((t) => t.capability === capability)
    setSelectedTemplate(matchingTemplate?.name ?? null)
    setEditingAgentId(agent.id)
    setTab("creator")
    setTimeout(() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50)
  }

  const handleSaveAgent = async () => {
    if (!agentName.trim() || !systemPrompt.trim()) return

    const template = TEMPLATES.find((t) => t.name === selectedTemplate)
    const config: Record<string, unknown> = {}
    if (template?.capability) config.capability = template.capability
    if (selectedModel) config.model = selectedModel

    setIsCreating(true)
    try {
      if (editingAgentId) {
        const existingAgent = agents.find((a) => a.id === editingAgentId)
        const updated = await api.agents.update(editingAgentId, {
          name: agentName,
          description: agentDescription || undefined,
          system_prompt: systemPrompt,
          config: { ...(existingAgent?.config ?? {}), ...config },
        })
        updateAgent(editingAgentId, updated)
      } else {
        const agent = await api.agents.create({
          name: agentName,
          system_prompt: systemPrompt,
          description: agentDescription || undefined,
          board_id: boardId,
          config,
        })
        addAgent(agent)
      }
      resetForm()
    } catch (error) {
      console.error("Failed to save agent:", error)
    } finally {
      setIsCreating(false)
    }
  }

  const handleDeleteAgent = async (id: string) => {
    if (editingAgentId === id) resetForm()
    try {
      await api.agents.delete(id)
      removeAgent(id)
      setTeamAgentSelection((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    } catch (error) {
      console.error("Failed to delete agent:", error)
    }
  }

  // ── Team helpers ────────────────────────────────────────────
  const openNewTeamDialog = () => {
    setEditingTeam(null)
    setTeamName("")
    setTeamDescription("")
    setTeamMembers({
      capabilities: new Set(teamCapabilitySelection),
      agentIds: new Set(teamAgentSelection),
    })
    setOrchSystemPrompt(DEFAULT_ORCHESTRATOR_PROMPT)
    setOrchModel(DEFAULT_ORCHESTRATOR_MODELS[0])
    setOrchTemperature(0.7)
    setOrchRouting("llm_routed")
    setOrchMaxCredits("")
    setTeamDialogOpen(true)
  }

  const applyTeamTemplate = (template: TeamTemplate) => {
    setEditingTeam(null)
    setTeamName(template.name)
    setTeamDescription(template.tagline)
    setTeamMembers({
      capabilities: new Set(template.capabilities),
      agentIds: new Set(template.agent_ids ?? []),
    })
    setOrchSystemPrompt(template.orchestrator.system_prompt)
    setOrchModel(template.orchestrator.model)
    setOrchTemperature(template.orchestrator.temperature)
    setOrchRouting(template.orchestrator.routing_strategy)
    setOrchMaxCredits("")
    setTeamDialogOpen(true)
  }

  const createTeamFromTemplate = async (template: TeamTemplate) => {
    setIsSavingTeam(true)
    try {
      const created = await api.teams.create({
        name: template.name,
        description: template.tagline,
        board_id: boardId,
        members: {
          capabilities: template.capabilities,
          agent_ids: template.agent_ids ?? [],
        },
        orchestrator: template.orchestrator,
      })
      addTeam(created)
    } catch (error) {
      console.error("Failed to create team from template:", error)
    } finally {
      setIsSavingTeam(false)
    }
  }

  const openEditTeamDialog = (team: Team) => {
    setEditingTeam(team)
    setTeamName(team.name)
    setTeamDescription(team.description ?? "")
    setTeamMembers({
      capabilities: new Set(team.members?.capabilities ?? []),
      agentIds: new Set(team.members?.agent_ids ?? []),
    })
    setOrchSystemPrompt(team.orchestrator?.system_prompt ?? DEFAULT_ORCHESTRATOR_PROMPT)
    setOrchModel(team.orchestrator?.model ?? DEFAULT_ORCHESTRATOR_MODELS[0])
    setOrchTemperature(team.orchestrator?.temperature ?? 0.7)
    setOrchRouting(team.orchestrator?.routing_strategy ?? "llm_routed")
    setOrchMaxCredits(
      team.orchestrator?.max_credits != null ? String(team.orchestrator.max_credits) : ""
    )
    setTeamDialogOpen(true)
  }

  const handleSaveTeam = async () => {
    if (!teamName.trim()) return
    setIsSavingTeam(true)
    try {
      const parsedCap = orchMaxCredits.trim() === "" ? null : parseInt(orchMaxCredits, 10)
      const maxCredits =
        parsedCap !== null && Number.isFinite(parsedCap) && parsedCap > 0 ? parsedCap : null
      const payload = {
        name: teamName,
        description: teamDescription || undefined,
        members: {
          capabilities: [...teamMembers.capabilities],
          agent_ids: [...teamMembers.agentIds],
        },
        orchestrator: {
          system_prompt: orchSystemPrompt,
          model: orchModel,
          temperature: orchTemperature,
          routing_strategy: orchRouting,
          max_credits: maxCredits,
        },
      }
      if (editingTeam) {
        const updated = await api.teams.update(editingTeam.id, payload)
        updateTeam(editingTeam.id, updated)
      } else {
        const created = await api.teams.create({ ...payload, board_id: boardId })
        addTeam(created)
      }
      setTeamDialogOpen(false)
      setTeamCapabilitySelection(new Set())
      setTeamAgentSelection(new Set())
    } catch (error) {
      console.error("Failed to save team:", error)
    } finally {
      setIsSavingTeam(false)
    }
  }

  const handleDeleteTeam = async (id: string) => {
    try {
      await api.teams.delete(id)
      removeTeam(id)
    } catch (error) {
      console.error("Failed to delete team:", error)
    }
  }

  // ── Derived ─────────────────────────────────────────────────
  const galleryItems = useMemo(() => {
    const customItems = agents.map((a) => ({ kind: "custom" as const, agent: a }))
    const presetItems = TEMPLATES.filter((t) => !!t.capability).map((t) => ({
      kind: "preset" as const,
      template: t,
    }))

    const all = [...customItems, ...presetItems]
    const filtered = all.filter((item) => {
      if (galleryCategory === "Custom") return item.kind === "custom"
      if (galleryCategory !== "All") {
        if (item.kind !== "preset") return false
        return item.template.category === galleryCategory
      }
      return true
    })

    if (!searchQuery.trim()) return filtered
    const q = searchQuery.toLowerCase()
    return filtered.filter((item) => {
      if (item.kind === "custom") {
        return (
          item.agent.name.toLowerCase().includes(q) ||
          (item.agent.description ?? "").toLowerCase().includes(q)
        )
      }
      return (
        item.template.name.toLowerCase().includes(q) ||
        item.template.description.toLowerCase().includes(q) ||
        (item.template.capability ?? "").toLowerCase().includes(q)
      )
    })
  }, [galleryCategory, searchQuery, agents])

  const selectionCount = teamCapabilitySelection.size + teamAgentSelection.size

  // ── Render ──────────────────────────────────────────────────
  return (
    <div className="relative h-screen flex flex-col overflow-hidden bg-background">
      {/* Ambient prism backdrop */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(800px circle at 10% -10%, oklch(0.72 0.2 350 / 22%), transparent 50%), radial-gradient(700px circle at 110% 110%, oklch(0.72 0.13 195 / 20%), transparent 55%), radial-gradient(900px circle at 50% 120%, oklch(0.62 0.22 295 / 16%), transparent 60%)",
        }}
      />

      {/* Header */}
      <header className="relative z-10 border-b border-border/60 bg-card/40 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1480px] items-center gap-6 px-6 py-4">
          <Button variant="ghost" size="icon" asChild aria-label="Go back">
            <Link href={`/boards/${boardId}`}>
              <ArrowLeft className="size-4" />
            </Link>
          </Button>
          <div className="flex items-center gap-3">
            <div className="relative flex size-9 items-center justify-center rounded-md">
              <div
                className="absolute inset-0 rounded-md opacity-80"
                style={{
                  background:
                    "conic-gradient(from 210deg at 50% 50%, var(--brand-pink), var(--primary), var(--brand-turquoise), var(--brand-pink))",
                }}
              />
              <Sparkles className="relative size-4 text-background" strokeWidth={2.5} />
            </div>
            <div>
              <p className="text-[10px] font-mono uppercase tracking-[0.3em] text-muted-foreground">
                Prism • Studio
              </p>
              <h1 className="font-heading text-lg font-medium tracking-tight">Agent Atelier</h1>
            </div>
          </div>

          {/* Tab rail */}
          <nav className="ml-auto flex items-end gap-1" role="tablist">
            {TABS.map((t) => {
              const Icon = t.icon
              const active = tab === t.key
              return (
                <button
                  key={t.key}
                  role="tab"
                  aria-selected={active}
                  onClick={() => setTab(t.key)}
                  className={cn(
                    "group/tab relative flex items-center gap-2 px-5 py-3 text-xs font-medium uppercase tracking-[0.22em] transition-colors",
                    active ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  <Icon className="size-3.5" />
                  <span>{t.label}</span>
                  {t.key === "teams" && teams.length > 0 && (
                    <span className="rounded-full bg-muted px-1.5 font-mono text-[9px] text-muted-foreground">
                      {teams.length}
                    </span>
                  )}
                  {/* Gradient underline */}
                  <span
                    aria-hidden
                    className={cn(
                      "absolute inset-x-3 -bottom-px h-[2px] rounded-full transition-all duration-300",
                      active ? "opacity-100 scale-x-100" : "opacity-0 scale-x-50 group-hover/tab:opacity-40"
                    )}
                    style={{
                      background:
                        "linear-gradient(90deg, var(--brand-pink), var(--primary), var(--brand-turquoise))",
                      boxShadow: active ? "0 0 12px oklch(0.62 0.22 295 / 50%)" : undefined,
                    }}
                  />
                </button>
              )
            })}
          </nav>
        </div>
      </header>

      {/* Content */}
      <main className="relative z-10 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1480px] px-6 py-8">
          {tab === "creator" && (
            <CreatorPanel
              templateCategory={templateCategory}
              setTemplateCategory={setTemplateCategory}
              selectedTemplate={selectedTemplate}
              onSelectTemplate={selectTemplate}
              agentName={agentName}
              setAgentName={setAgentName}
              agentDescription={agentDescription}
              setAgentDescription={setAgentDescription}
              systemPrompt={systemPrompt}
              setSystemPrompt={setSystemPrompt}
              selectedModel={selectedModel}
              setSelectedModel={setSelectedModel}
              editingAgentId={editingAgentId}
              isCreating={isCreating}
              onSave={handleSaveAgent}
              onCancel={resetForm}
              formRef={formRef}
            />
          )}

          {tab === "agents" && (
            <AgentsPanel
              boardId={boardId}
              isLoading={isLoading}
              galleryItems={galleryItems}
              galleryCategory={galleryCategory}
              setGalleryCategory={setGalleryCategory}
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              teamCapabilitySelection={teamCapabilitySelection}
              setTeamCapabilitySelection={setTeamCapabilitySelection}
              teamAgentSelection={teamAgentSelection}
              setTeamAgentSelection={setTeamAgentSelection}
              selectionCount={selectionCount}
              onBuildTeam={openNewTeamDialog}
              onUseAsTemplate={selectTemplate}
              onEditAgent={loadAgentIntoForm}
              onDeleteAgent={handleDeleteAgent}
            />
          )}

          {tab === "teams" && (
            <TeamsPanel
              boardId={boardId}
              isLoading={isLoading}
              teams={teams}
              agents={agents}
              onNewTeam={openNewTeamDialog}
              onEditTeam={openEditTeamDialog}
              onDeleteTeam={handleDeleteTeam}
              onApplyTemplate={applyTeamTemplate}
              onCreateFromTemplate={createTeamFromTemplate}
              isCreatingFromTemplate={isSavingTeam}
            />
          )}
        </div>
      </main>

      {/* Team editor dialog */}
      <Dialog open={teamDialogOpen} onOpenChange={setTeamDialogOpen}>
        <DialogContent className="max-w-3xl w-[calc(100%-2rem)] p-0 sm:max-w-3xl overflow-hidden">
          <div
            aria-hidden
            className="absolute inset-x-0 top-0 h-[2px]"
            style={{
              background:
                "linear-gradient(90deg, var(--brand-pink), var(--primary), var(--brand-turquoise))",
            }}
          />
          <div className="max-h-[85vh] overflow-y-auto p-6">
            <DialogHeader className="mb-6">
              <DialogTitle className="font-heading text-xl tracking-tight">
                {editingTeam ? "Edit team" : "Assemble a team"}
              </DialogTitle>
              <DialogDescription>
                Pick members, configure the orchestrator, and deploy as a coordinated crew.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-6">
              {!editingTeam && (
                <section className="space-y-2">
                  <Label>Start from a template</Label>
                  <div className="grid gap-2 sm:grid-cols-3">
                    {TEAM_TEMPLATES.map((tpl) => (
                      <button
                        key={tpl.slug}
                        type="button"
                        onClick={() => applyTeamTemplate(tpl)}
                        className="group flex items-start gap-2 rounded-md border border-border/60 bg-card/40 p-2 text-left transition-all hover:-translate-y-px hover:border-primary/40"
                      >
                        <span className="text-lg leading-none">{tpl.accent}</span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-xs font-medium">{tpl.name}</p>
                          <p className="line-clamp-2 text-[10px] text-muted-foreground">
                            {tpl.tagline}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                </section>
              )}

              {/* Identity */}
              <section className="grid gap-3 sm:grid-cols-[1fr_1.6fr]">
                <div className="space-y-1.5">
                  <Label>Team name</Label>
                  <Input
                    placeholder="The Art Dept."
                    value={teamName}
                    onChange={(e) => setTeamName(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Description</Label>
                  <Input
                    placeholder="What does this team do?"
                    value={teamDescription}
                    onChange={(e) => setTeamDescription(e.target.value)}
                  />
                </div>
              </section>

              {/* Members */}
              <section className="space-y-3">
                <div className="flex items-baseline justify-between">
                  <Label>Members</Label>
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                    {teamMembers.capabilities.size + teamMembers.agentIds.size} selected
                  </span>
                </div>
                <div className="grid max-h-[260px] gap-1.5 overflow-y-auto rounded-lg border border-border/60 bg-muted/20 p-2 sm:grid-cols-2">
                  {/* Custom agents first */}
                  {agents.map((a) => {
                    const checked = teamMembers.agentIds.has(a.id)
                    return (
                      <MemberToggle
                        key={`a-${a.id}`}
                        checked={checked}
                        onToggle={() =>
                          setTeamMembers((prev) => {
                            const next = new Set(prev.agentIds)
                            if (next.has(a.id)) next.delete(a.id)
                            else next.add(a.id)
                            return { ...prev, agentIds: next }
                          })
                        }
                        label={a.name}
                        sub={(a.config?.model as string) ?? "custom agent"}
                        tone="pink"
                      />
                    )
                  })}
                  {/* Presets */}
                  {TEMPLATES.filter((t) => !!t.capability).map((t) => {
                    const checked = teamMembers.capabilities.has(t.capability!)
                    return (
                      <MemberToggle
                        key={`t-${t.capability}`}
                        checked={checked}
                        onToggle={() =>
                          setTeamMembers((prev) => {
                            const next = new Set(prev.capabilities)
                            if (next.has(t.capability!)) next.delete(t.capability!)
                            else next.add(t.capability!)
                            return { ...prev, capabilities: next }
                          })
                        }
                        label={`${t.icon} ${t.name}`}
                        sub={t.defaultModel?.split("/").slice(-1)[0] ?? t.capability!}
                        tone="turquoise"
                      />
                    )
                  })}
                </div>
              </section>

              {/* Orchestrator */}
              <section className="space-y-3 rounded-lg border border-border/60 bg-muted/10 p-4">
                <header className="flex items-center gap-2">
                  <Radar className="size-3.5 text-[color:var(--brand-turquoise)]" />
                  <h3 className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">
                    Orchestrator
                  </h3>
                </header>
                <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
                  <div className="space-y-1.5">
                    <Label>Model</Label>
                    <select
                      value={orchModel}
                      onChange={(e) => setOrchModel(e.target.value)}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                      {DEFAULT_ORCHESTRATOR_MODELS.map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <Label>Temperature</Label>
                    <div className="flex items-center gap-3">
                      <input
                        type="range"
                        min={0}
                        max={2}
                        step={0.1}
                        value={orchTemperature}
                        onChange={(e) => setOrchTemperature(parseFloat(e.target.value))}
                        className="flex-1 accent-[color:var(--primary)]"
                      />
                      <span className="font-mono text-sm tabular-nums w-10 text-right">
                        {orchTemperature.toFixed(1)}
                      </span>
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <Label>Spend cap</Label>
                    <div className="flex items-center gap-1.5">
                      <Input
                        type="number"
                        min={1}
                        step={1}
                        value={orchMaxCredits}
                        onChange={(e) => setOrchMaxCredits(e.target.value)}
                        placeholder="∞"
                        className="w-20 text-sm tabular-nums"
                      />
                      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                        cr / run
                      </span>
                    </div>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label>Routing strategy</Label>
                  <div className="flex flex-wrap gap-2">
                    {ROUTING_STRATEGIES.map((s) => (
                      <button
                        key={s.value}
                        type="button"
                        onClick={() => setOrchRouting(s.value)}
                        className={cn(
                          "group relative flex flex-col items-start rounded-md border px-3 py-2 text-left transition-all",
                          orchRouting === s.value
                            ? "border-primary/60 bg-primary/5"
                            : "border-border/60 hover:border-border bg-card/40"
                        )}
                      >
                        <span className="text-xs font-medium">{s.label}</span>
                        <span className="text-[10px] text-muted-foreground">{s.hint}</span>
                        {orchRouting === s.value && (
                          <Check className="absolute right-2 top-2 size-3 text-primary" />
                        )}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label>System prompt</Label>
                  <Textarea
                    className="min-h-[140px] font-mono text-xs leading-relaxed"
                    value={orchSystemPrompt}
                    onChange={(e) => setOrchSystemPrompt(e.target.value)}
                  />
                </div>
              </section>
            </div>

            <footer className="sticky bottom-0 -mx-6 mt-6 flex items-center justify-between gap-2 border-t border-border/60 bg-popover/90 px-6 py-4 backdrop-blur-xl">
              <Button variant="ghost" onClick={() => setTeamDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleSaveTeam}
                disabled={!teamName.trim() || isSavingTeam}
                className="gap-2"
              >
                {isSavingTeam ? "Saving…" : editingTeam ? "Save team" : "Create team"}
              </Button>
            </footer>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ────────────────────────────────────────────────────────────────
// Creator panel
// ────────────────────────────────────────────────────────────────

function CreatorPanel(props: {
  templateCategory: Exclude<Category, "Custom">
  setTemplateCategory: (c: Exclude<Category, "Custom">) => void
  selectedTemplate: string | null
  onSelectTemplate: (name: string) => void
  agentName: string
  setAgentName: (s: string) => void
  agentDescription: string
  setAgentDescription: (s: string) => void
  systemPrompt: string
  setSystemPrompt: (s: string) => void
  selectedModel: string
  setSelectedModel: (s: string) => void
  editingAgentId: string | null
  isCreating: boolean
  onSave: () => void
  onCancel: () => void
  formRef: React.RefObject<HTMLDivElement | null>
}) {
  const {
    templateCategory,
    setTemplateCategory,
    selectedTemplate,
    onSelectTemplate,
    agentName,
    setAgentName,
    agentDescription,
    setAgentDescription,
    systemPrompt,
    setSystemPrompt,
    selectedModel,
    setSelectedModel,
    editingAgentId,
    isCreating,
    onSave,
    onCancel,
    formRef,
  } = props

  const template = TEMPLATES.find((t) => t.name === selectedTemplate)
  const templateCats = CATEGORIES.filter((c) => c !== "Custom") as readonly Exclude<
    Category,
    "Custom"
  >[]

  return (
    <section className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
      {/* Left: template picker */}
      <div className="space-y-4">
        <SectionHeader
          eyebrow="Step 01"
          title="Start from a template"
          hint="Or build from scratch on the right — skip this and fill the form."
        />

        <ChipRow
          items={templateCats.map((c) => ({ value: c, label: c }))}
          active={templateCategory}
          onChange={(v) => setTemplateCategory(v as Exclude<Category, "Custom">)}
        />

        <div className="grid gap-2.5 sm:grid-cols-2">
          {TEMPLATES.filter(
            (t) => templateCategory === "All" || t.category === templateCategory
          ).map((t) => {
            const active = selectedTemplate === t.name
            return (
              <button
                key={t.name}
                onClick={() => onSelectTemplate(t.name)}
                className={cn(
                  "group relative flex items-start gap-3 rounded-xl border p-3 text-left transition-all",
                  "hover:-translate-y-px hover:border-primary/40",
                  active
                    ? "border-primary/60 bg-primary/5 shadow-accent-glow"
                    : "border-border/60 bg-card/40"
                )}
              >
                <span className="text-2xl leading-none">{t.icon}</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{t.name}</p>
                  <p className="line-clamp-2 text-xs text-muted-foreground">{t.description}</p>
                  {t.defaultModel && (
                    <code className="mt-1.5 inline-block rounded-sm bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                      {t.defaultModel.split("/").slice(-1)[0]}
                    </code>
                  )}
                </div>
                {active && (
                  <div
                    aria-hidden
                    className="absolute left-0 top-3 h-[calc(100%-1.5rem)] w-[2px] rounded-full"
                    style={{
                      background:
                        "linear-gradient(180deg, var(--brand-pink), var(--primary), var(--brand-turquoise))",
                    }}
                  />
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Right: form */}
      <div ref={formRef} className="space-y-4">
        <SectionHeader
          eyebrow={editingAgentId ? "Editing" : "Step 02"}
          title={editingAgentId ? "Refine your agent" : "Compose the agent"}
          hint={
            editingAgentId
              ? "Changes save to this existing agent."
              : "Define the brief, the system prompt, and the model."
          }
          tone={editingAgentId ? "editing" : "default"}
        />

        <PrismCard
          className={cn(
            "space-y-5 p-5",
            editingAgentId && "ring-1 ring-[color:var(--brand-pink)]/60"
          )}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Agent name</Label>
              <Input
                placeholder="My Custom Agent"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Description</Label>
              <Input
                placeholder="What does it do?"
                value={agentDescription}
                onChange={(e) => setAgentDescription(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>System prompt</Label>
            <Textarea
              placeholder="You are a helpful AI assistant that…"
              className="min-h-[220px] font-mono text-xs leading-relaxed"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
            />
          </div>

          {template?.modelChoices && (
            <div className="space-y-1.5">
              <Label>Model</Label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {template.modelChoices.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          )}
          {template && !template.modelChoices && template.defaultModel && (
            <div className="space-y-1.5">
              <Label>Model</Label>
              <div className="rounded-md border border-input bg-muted/40 px-3 py-2 font-mono text-xs">
                {template.defaultModel}
              </div>
            </div>
          )}

          <div className="flex items-center gap-2 pt-1">
            <Button
              onClick={onSave}
              disabled={!agentName.trim() || !systemPrompt.trim() || isCreating}
              className="flex-1 gap-2"
            >
              {isCreating ? (
                "Saving…"
              ) : editingAgentId ? (
                <>
                  <Check className="size-4" />
                  Save changes
                </>
              ) : (
                <>
                  <Plus className="size-4" />
                  Create agent
                </>
              )}
            </Button>
            {editingAgentId && (
              <Button variant="outline" onClick={onCancel} className="gap-1.5">
                <X className="size-3.5" />
                Cancel
              </Button>
            )}
          </div>
        </PrismCard>
      </div>
    </section>
  )
}

// ────────────────────────────────────────────────────────────────
// Agents panel
// ────────────────────────────────────────────────────────────────

type GalleryItem =
  | { kind: "custom"; agent: Agent }
  | { kind: "preset"; template: Template }

function AgentsPanel(props: {
  boardId: string
  isLoading: boolean
  galleryItems: GalleryItem[]
  galleryCategory: Category
  setGalleryCategory: (c: Category) => void
  searchQuery: string
  setSearchQuery: (s: string) => void
  teamCapabilitySelection: Set<string>
  setTeamCapabilitySelection: React.Dispatch<React.SetStateAction<Set<string>>>
  teamAgentSelection: Set<string>
  setTeamAgentSelection: React.Dispatch<React.SetStateAction<Set<string>>>
  selectionCount: number
  onBuildTeam: () => void
  onUseAsTemplate: (name: string) => void
  onEditAgent: (agent: Agent) => void
  onDeleteAgent: (id: string) => void
}) {
  const {
    boardId,
    isLoading,
    galleryItems,
    galleryCategory,
    setGalleryCategory,
    searchQuery,
    setSearchQuery,
    teamCapabilitySelection,
    setTeamCapabilitySelection,
    teamAgentSelection,
    setTeamAgentSelection,
    selectionCount,
    onBuildTeam,
    onUseAsTemplate,
    onEditAgent,
    onDeleteAgent,
  } = props

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <SectionHeader
          eyebrow="The roster"
          title="Agents"
          hint="Every preset specialist plus every custom agent you've built."
        />
        {selectionCount > 0 && (
          <Button onClick={onBuildTeam} className="gap-2 shadow-accent-glow">
            <Users className="size-4" />
            Forge team from selection ({selectionCount})
          </Button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <ChipRow
          items={CATEGORIES.map((c) => ({ value: c, label: c }))}
          active={galleryCategory}
          onChange={(v) => setGalleryCategory(v as Category)}
        />
        <div className="relative ml-auto w-full max-w-[280px]">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search agents…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 text-sm"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-[170px] w-full" />
          ))}
        </div>
      ) : galleryItems.length === 0 ? (
        <EmptyState
          icon={<Layers className="size-10 text-muted-foreground/40" />}
          title="Nothing matches that filter"
          hint="Try a different category or clear the search."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {galleryItems.map((item) =>
            item.kind === "custom" ? (
              <CustomAgentCard
                key={`a-${item.agent.id}`}
                agent={item.agent}
                boardId={boardId}
                checked={teamAgentSelection.has(item.agent.id)}
                onToggle={() =>
                  setTeamAgentSelection((prev) => {
                    const next = new Set(prev)
                    if (next.has(item.agent.id)) next.delete(item.agent.id)
                    else next.add(item.agent.id)
                    return next
                  })
                }
                onEdit={() => onEditAgent(item.agent)}
                onDelete={() => onDeleteAgent(item.agent.id)}
              />
            ) : (
              <PresetAgentCard
                key={`t-${item.template.capability}`}
                template={item.template}
                boardId={boardId}
                checked={teamCapabilitySelection.has(item.template.capability!)}
                onToggle={() =>
                  setTeamCapabilitySelection((prev) => {
                    const next = new Set(prev)
                    if (next.has(item.template.capability!)) next.delete(item.template.capability!)
                    else next.add(item.template.capability!)
                    return next
                  })
                }
                onUseAsTemplate={() => onUseAsTemplate(item.template.name)}
              />
            )
          )}
        </div>
      )}
    </section>
  )
}

function PresetAgentCard(props: {
  template: Template
  boardId: string
  checked: boolean
  onToggle: () => void
  onUseAsTemplate: () => void
}) {
  const { template, boardId, checked, onToggle, onUseAsTemplate } = props
  return (
    <PrismCard
      className={cn(
        "group relative flex flex-col gap-3 p-4 transition-all hover:-translate-y-0.5",
        checked && "ring-2 ring-[color:var(--brand-turquoise)]/70 shadow-accent-glow"
      )}
    >
      <Selector checked={checked} onToggle={onToggle} tone="turquoise" />
      <div className="flex items-start gap-3 pr-8">
        <span className="text-3xl leading-none">{template.icon}</span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate font-medium">{template.name}</h3>
            <Badge
              variant="outline"
              className="border-[color:var(--brand-turquoise)]/40 text-[9px] uppercase tracking-[0.18em] text-[color:var(--brand-turquoise)]"
            >
              Preset
            </Badge>
          </div>
          <p className="line-clamp-2 text-xs text-muted-foreground">{template.description}</p>
        </div>
      </div>
      <div className="flex items-center gap-2 text-[10px]">
        {template.defaultModel && (
          <code className="truncate rounded-sm bg-muted px-1.5 py-0.5 font-mono text-muted-foreground">
            {template.defaultModel}
          </code>
        )}
        {template.capability && (
          <code className="rounded-sm bg-primary/10 px-1.5 py-0.5 font-mono text-[color:var(--primary)]">
            {template.capability}
          </code>
        )}
      </div>
      <div className="mt-auto flex items-center gap-2 pt-1">
        <Button variant="outline" size="sm" className="flex-1 gap-1.5" asChild>
          <Link href={`/boards/${boardId}?capability=${template.capability}`}>
            <Play className="size-3" />
            Run solo
          </Link>
        </Button>
        <Button variant="ghost" size="sm" onClick={onUseAsTemplate} className="gap-1.5">
          <Wand2 className="size-3" />
          Fork
        </Button>
      </div>
    </PrismCard>
  )
}

function CustomAgentCard(props: {
  agent: Agent
  boardId: string
  checked: boolean
  onToggle: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  const { agent, boardId, checked, onToggle, onEdit, onDelete } = props
  return (
    <PrismCard
      className={cn(
        "group relative flex flex-col gap-3 p-4 transition-all hover:-translate-y-0.5",
        checked && "ring-2 ring-[color:var(--brand-pink)]/70 shadow-accent-glow"
      )}
    >
      <Selector checked={checked} onToggle={onToggle} tone="pink" />
      <div className="flex items-start gap-3 pr-8">
        <div
          className="flex size-10 items-center justify-center rounded-md font-mono text-sm uppercase"
          style={{
            background:
              "linear-gradient(135deg, oklch(0.72 0.2 350 / 20%), oklch(0.72 0.13 195 / 20%))",
          }}
        >
          {agent.name.slice(0, 2)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate font-medium">{agent.name}</h3>
            <Badge
              variant="outline"
              className="border-[color:var(--brand-pink)]/40 text-[9px] uppercase tracking-[0.18em] text-[color:var(--brand-pink)]"
            >
              Custom
            </Badge>
          </div>
          {agent.description && (
            <p className="line-clamp-2 text-xs text-muted-foreground">{agent.description}</p>
          )}
        </div>
      </div>
      <p className="line-clamp-2 font-mono text-[10px] leading-relaxed text-muted-foreground/70">
        {agent.system_prompt}
      </p>
      <div className="mt-auto flex items-center gap-2 pt-1">
        <Button variant="outline" size="sm" className="flex-1 gap-1.5" asChild>
          <Link href={`/boards/${boardId}?agent_id=${agent.id}`}>
            <Play className="size-3" />
            Run
          </Link>
        </Button>
        <Button variant="ghost" size="sm" onClick={onEdit} className="gap-1.5">
          <Pencil className="size-3" />
          Edit
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={onDelete}
          className="size-8 text-destructive"
          title="Delete"
          aria-label="Delete"
        >
          <Trash2 className="size-3.5" />
        </Button>
      </div>
    </PrismCard>
  )
}

// ────────────────────────────────────────────────────────────────
// Teams panel
// ────────────────────────────────────────────────────────────────

function TeamsPanel(props: {
  boardId: string
  isLoading: boolean
  teams: Team[]
  agents: Agent[]
  onNewTeam: () => void
  onEditTeam: (team: Team) => void
  onDeleteTeam: (id: string) => void
  onApplyTemplate: (template: TeamTemplate) => void
  onCreateFromTemplate: (template: TeamTemplate) => void
  isCreatingFromTemplate: boolean
}) {
  const {
    boardId,
    isLoading,
    teams,
    agents,
    onNewTeam,
    onEditTeam,
    onDeleteTeam,
    onApplyTemplate,
    onCreateFromTemplate,
    isCreatingFromTemplate,
  } = props

  const agentMap = useMemo(() => new Map(agents.map(a => [a.id, a])), [agents])

  return (
    <section className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <SectionHeader
          eyebrow="Coordinated crews"
          title="Teams"
          hint="Each team routes through its own orchestrator and members."
        />
        <Button onClick={onNewTeam} className="gap-2 shadow-accent-glow">
          <Plus className="size-4" />
          New team
        </Button>
      </div>

      {/* Starter templates — always visible as reference examples */}
      <div className="space-y-3">
        <div className="flex items-baseline justify-between">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            Example teams · drop-in starters
          </p>
          <p className="text-[11px] text-muted-foreground">
            Tap <span className="font-medium text-foreground">Use</span> to drop into your roster · or <span className="font-medium text-foreground">Customize</span> to tweak first.
          </p>
        </div>
        <div className="grid gap-3 lg:grid-cols-3">
          {TEAM_TEMPLATES.map((tpl) => (
            <TeamTemplateCard
              key={tpl.slug}
              template={tpl}
              busy={isCreatingFromTemplate}
              onUse={() => onCreateFromTemplate(tpl)}
              onCustomize={() => onApplyTemplate(tpl)}
            />
          ))}
        </div>
      </div>

      {/* Saved teams */}
      <div className="space-y-3">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          Your saved teams
        </p>

        {isLoading ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {[1, 2].map((i) => (
              <Skeleton key={i} className="h-[200px] w-full" />
            ))}
          </div>
        ) : teams.length === 0 ? (
          <EmptyState
            icon={<Users className="size-10 text-muted-foreground/40" />}
            title="No saved teams yet"
            hint="Use one of the example teams above, or build a fresh one from scratch."
            action={
              <Button onClick={onNewTeam} className="gap-2 mt-3" variant="outline">
                <Plus className="size-4" />
                Build from scratch
              </Button>
            }
          />
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            {teams.map((team) => (
              <TeamCard
                key={team.id}
                team={team}
                agentMap={agentMap}
                boardId={boardId}
                onEdit={() => onEditTeam(team)}
                onDelete={() => onDeleteTeam(team.id)}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

function TeamTemplateCard(props: {
  template: TeamTemplate
  busy: boolean
  onUse: () => void
  onCustomize: () => void
}) {
  const { template, busy, onUse, onCustomize } = props
  const memberCount = template.capabilities.length + (template.agent_ids?.length ?? 0)
  const previewCaps = template.capabilities
    .map((c) => TEMPLATES_BY_CAPABILITY.get(c))
    .filter((t): t is Template => Boolean(t))
    .slice(0, 6)

  return (
    <PrismCard className="group relative flex flex-col gap-3 overflow-hidden p-5 transition-all hover:-translate-y-0.5">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.04] transition-opacity group-hover:opacity-[0.08]"
        style={{
          background:
            "conic-gradient(from 200deg at 0% 0%, var(--brand-pink), var(--primary), var(--brand-turquoise), var(--brand-pink))",
        }}
      />
      <div className="relative flex items-start gap-3">
        <div
          className="flex size-12 shrink-0 items-center justify-center rounded-lg text-2xl"
          style={{
            background:
              "linear-gradient(135deg, oklch(0.72 0.2 350 / 18%), oklch(0.62 0.22 295 / 14%), oklch(0.72 0.13 195 / 18%))",
          }}
        >
          {template.accent}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-heading text-base font-medium tracking-tight">{template.name}</h3>
          <p className="text-xs text-muted-foreground">{template.tagline}</p>
        </div>
      </div>

      <p className="relative line-clamp-3 text-xs leading-relaxed text-muted-foreground/90">
        {template.description}
      </p>

      <div className="relative flex flex-wrap gap-1">
        {previewCaps.map((t) => (
          <span
            key={t.capability}
            title={t.name}
            className="inline-flex items-center gap-1 rounded-full border border-border/60 bg-card/60 px-1.5 py-0.5 text-[10px]"
          >
            <span>{t.icon}</span>
            <span className="font-mono text-muted-foreground">
              {t.capability}
            </span>
          </span>
        ))}
        {memberCount > previewCaps.length && (
          <span className="text-[10px] text-muted-foreground">
            +{memberCount - previewCaps.length}
          </span>
        )}
      </div>

      <dl className="relative grid grid-cols-3 gap-2 rounded-md border border-border/40 bg-muted/20 p-2 text-[10px]">
        <div className="min-w-0">
          <dt className="font-mono uppercase tracking-[0.18em] text-muted-foreground/70">Model</dt>
          <dd className="truncate font-mono">
            {template.orchestrator.model.split("/").slice(-1)[0]}
          </dd>
        </div>
        <div className="min-w-0">
          <dt className="font-mono uppercase tracking-[0.18em] text-muted-foreground/70">Route</dt>
          <dd className="truncate">
            {ROUTING_STRATEGIES.find((s) => s.value === template.orchestrator.routing_strategy)
              ?.label ?? "—"}
          </dd>
        </div>
        <div className="min-w-0">
          <dt className="font-mono uppercase tracking-[0.18em] text-muted-foreground/70">Temp</dt>
          <dd className="font-mono tabular-nums">
            {template.orchestrator.temperature.toFixed(1)}
          </dd>
        </div>
      </dl>

      <div className="relative mt-auto flex items-center gap-2 pt-1">
        <Button
          onClick={onUse}
          disabled={busy}
          size="sm"
          className="flex-1 gap-1.5 shadow-accent-glow"
        >
          <Sparkles className="size-3.5" />
          {busy ? "Adding…" : "Use this team"}
        </Button>
        <Button onClick={onCustomize} size="sm" variant="outline" className="gap-1.5">
          <Pencil className="size-3.5" />
          Customize
        </Button>
      </div>
    </PrismCard>
  )
}

function TeamCard(props: {
  team: Team
  agentMap: Map<string, Agent>
  boardId: string
  onEdit: () => void
  onDelete: () => void
}) {
  const { team, agentMap, boardId, onEdit, onDelete } = props
  const capCount = team.members?.capabilities?.length ?? 0
  const agentCount = team.members?.agent_ids?.length ?? 0
  const totalMembers = capCount + agentCount

  const capabilityChips = (team.members?.capabilities ?? [])
    .map((c) => TEMPLATES_BY_CAPABILITY.get(c))
    .filter((t): t is Template => Boolean(t))

  const agentsById = new Map(agents.map((a) => [a.id, a]))
  const agentChips = (team.members?.agent_ids ?? [])
    .map((id) => agentsById.get(id))
    .map((id) => agentMap.get(id))
    .filter((a): a is Agent => Boolean(a))

  const routing = ROUTING_STRATEGIES.find(
    (s) => s.value === team.orchestrator?.routing_strategy
  )

  return (
    <PrismCard className="group relative flex flex-col gap-4 overflow-hidden p-5">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 -top-px h-[2px] opacity-60"
        style={{
          background:
            "linear-gradient(90deg, var(--brand-pink), var(--primary), var(--brand-turquoise))",
        }}
      />
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-heading text-lg font-medium tracking-tight">{team.name}</h3>
          {team.description && (
            <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
              {team.description}
            </p>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="size-8" onClick={onEdit} title="Edit" aria-label="Edit">
            <Pencil className="size-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-destructive"
            onClick={onDelete}
            title="Delete"
            aria-label="Delete"
          >
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-1.5">
        {capabilityChips.slice(0, 6).map((t) => (
          <span
            key={t.capability}
            className="inline-flex items-center gap-1 rounded-full border border-[color:var(--brand-turquoise)]/30 bg-[color:var(--brand-turquoise)]/5 px-2 py-0.5 text-[10px]"
            title={t.name}
          >
            <span>{t.icon}</span>
            <span className="truncate max-w-[90px]">{t.name}</span>
          </span>
        ))}
        {agentChips.slice(0, 4).map((a) => (
          <span
            key={a.id}
            className="inline-flex items-center gap-1 rounded-full border border-[color:var(--brand-pink)]/30 bg-[color:var(--brand-pink)]/5 px-2 py-0.5 text-[10px]"
            title={a.name}
          >
            <span className="font-mono uppercase">{a.name.slice(0, 2)}</span>
            <span className="truncate max-w-[90px]">{a.name}</span>
          </span>
        ))}
        {totalMembers > 10 && (
          <span className="text-[10px] text-muted-foreground">+{totalMembers - 10} more</span>
        )}
        {totalMembers === 0 && (
          <span className="text-[11px] italic text-muted-foreground/70">No members yet</span>
        )}
      </div>

      <dl className="grid grid-cols-3 gap-3 rounded-md border border-border/40 bg-muted/20 p-3 text-[10px]">
        <div className="flex items-center gap-1.5">
          <Cpu className="size-3 text-muted-foreground" />
          <div className="min-w-0">
            <dt className="font-mono uppercase tracking-[0.18em] text-muted-foreground/70">
              Model
            </dt>
            <dd className="truncate font-mono">
              {team.orchestrator?.model?.split("/").slice(-1)[0] ?? "—"}
            </dd>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <Radar className="size-3 text-muted-foreground" />
          <div className="min-w-0">
            <dt className="font-mono uppercase tracking-[0.18em] text-muted-foreground/70">
              Route
            </dt>
            <dd className="truncate">{routing?.label ?? "—"}</dd>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <Users className="size-3 text-muted-foreground" />
          <div className="min-w-0">
            <dt className="font-mono uppercase tracking-[0.18em] text-muted-foreground/70">
              Members
            </dt>
            <dd className="font-mono tabular-nums">{totalMembers}</dd>
          </div>
        </div>
      </dl>

      <Button variant="outline" className="gap-2" asChild>
        <Link href={`/boards/${boardId}?team_id=${team.id}`}>
          <Play className="size-3.5" />
          Run team
        </Link>
      </Button>
    </PrismCard>
  )
}

// ────────────────────────────────────────────────────────────────
// Shared primitives
// ────────────────────────────────────────────────────────────────

function SectionHeader(props: {
  eyebrow: string
  title: string
  hint?: string
  tone?: "default" | "editing"
}) {
  const { eyebrow, title, hint, tone = "default" } = props
  return (
    <div className="space-y-1">
      <p
        className={cn(
          "font-mono text-[10px] uppercase tracking-[0.28em]",
          tone === "editing" ? "text-[color:var(--brand-pink)]" : "text-muted-foreground"
        )}
      >
        {eyebrow}
      </p>
      <h2 className="font-heading text-2xl font-medium tracking-tight">{title}</h2>
      {hint && <p className="text-sm text-muted-foreground">{hint}</p>}
    </div>
  )
}

function PrismCard({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border/60 bg-card/70 backdrop-blur-xl transition-colors",
        "hover:border-border",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

function ChipRow<T extends string>(props: {
  items: { value: T; label: string }[]
  active: T
  onChange: (v: T) => void
}) {
  return (
    <div className="flex flex-wrap gap-1">
      {props.items.map((item) => {
        const active = props.active === item.value
        return (
          <button
            key={item.value}
            onClick={() => props.onChange(item.value)}
            className={cn(
              "rounded-full border px-3 py-1 text-[11px] font-medium uppercase tracking-[0.16em] transition-all",
              active
                ? "border-transparent text-background"
                : "border-border/60 bg-transparent text-muted-foreground hover:text-foreground"
            )}
            style={
              active
                ? {
                    background:
                      "linear-gradient(90deg, var(--brand-pink), var(--primary), var(--brand-turquoise))",
                  }
                : undefined
            }
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label className="block font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
      {children}
    </label>
  )
}

function Selector({
  checked,
  onToggle,
  tone,
}: {
  checked: boolean
  onToggle: () => void
  tone: "pink" | "turquoise"
}) {
  const toneColor = tone === "pink" ? "var(--brand-pink)" : "var(--brand-turquoise)"
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={checked}
      title="Include in team"
      className={cn(
        "absolute right-3 top-3 flex size-5 items-center justify-center rounded-full border transition-all",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        checked ? "border-transparent" : "border-border/80 bg-background/60 hover:border-foreground/40"
      )}
      style={checked ? { background: toneColor, color: "oklch(0.16 0.02 290)" } : undefined}
    >
      {checked && <Check className="size-3" strokeWidth={3} />}
    </button>
  )
}

function MemberToggle(props: {
  checked: boolean
  onToggle: () => void
  label: string
  sub: string
  tone: "pink" | "turquoise"
}) {
  const { checked, onToggle, label, sub, tone } = props
  const toneColor = tone === "pink" ? "var(--brand-pink)" : "var(--brand-turquoise)"
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={checked}
      className={cn(
        "flex items-center gap-2 rounded-md border px-2.5 py-2 text-left transition-all",
        checked
          ? "border-transparent bg-card/80"
          : "border-border/60 bg-card/30 hover:border-border"
      )}
      style={
        checked ? { boxShadow: `inset 0 0 0 1px ${toneColor}`, } : undefined
      }
    >
      <div
        className={cn(
          "flex size-4 shrink-0 items-center justify-center rounded-sm border transition-colors",
          checked ? "border-transparent" : "border-border/80"
        )}
        style={
          checked ? { background: toneColor, color: "oklch(0.16 0.02 290)" } : undefined
        }
      >
        {checked && <Check className="size-2.5" strokeWidth={3} />}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-medium">{label}</p>
        <p className="truncate font-mono text-[10px] text-muted-foreground">{sub}</p>
      </div>
    </button>
  )
}

function EmptyState(props: {
  icon: React.ReactNode
  title: string
  hint?: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border/60 bg-card/20 py-16 text-center">
      {props.icon}
      <p className="font-heading text-base">{props.title}</p>
      {props.hint && (
        <p className="max-w-sm text-sm text-muted-foreground">{props.hint}</p>
      )}
      {props.action}
    </div>
  )
}
