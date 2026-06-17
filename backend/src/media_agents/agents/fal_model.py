"""Custom PydanticAI model that proxies chat completions through fal.ai.

fal.ai hosts an OpenAI-compatible OpenRouter chat-completions endpoint at
`openrouter/router/openai/v1/chat/completions`. It accepts the standard
OpenAI-style `messages` + `tools` payload and returns `choices[0].message`
with optional `tool_calls`, so we can keep PydanticAI's typed tool-calling flow.

Why this adapter exists: PydanticAI has no native fal.ai provider. We require
the fal.ai path (no new API keys). fal.ai's older `fal-ai/openrouter/chat/completions`
no longer resolves — the current id is under the `openrouter/` namespace.

The adapter calls `fal_client.run_async(...)` and returns a single full
`ModelResponse`, so `the agent run method` is the appropriate call pattern. fal.ai
itself supports streaming (`fal_client.stream_async`); we just don't use it
here. The user-visible SSE stream is driven by the orchestrator chunking
its output, not by token-level LLM streaming.
"""

from __future__ import annotations

import asyncio
import contextvars
import json
from typing import Any

import fal_client
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.tools import ToolDefinition

_FAL_CHAT_ENDPOINT = "openrouter/router/openai/v1/chat/completions"
_DEFAULT_MODEL = "openai/gpt-4o"

# Task-local holder for attachments during an agent run.
# Set by the orchestrator before calling the agent run method, cleared after.
_current_attachments: contextvars.ContextVar[list[dict[str, Any]] | None] = contextvars.ContextVar(
    "current_attachments", default=None
)


def set_current_attachments(attachments: list[dict[str, Any]] | None) -> contextvars.Token:
    """Set task-local attachments for the current agent run."""
    return _current_attachments.set(attachments)


def reset_current_attachments(token: contextvars.Token) -> None:
    """Reset task-local attachments to their previous state."""
    _current_attachments.reset(token)


def get_current_attachments() -> list[dict[str, Any]] | None:
    """Get the current task-local attachments."""
    return _current_attachments.get()


async def _messages_to_openai(
    messages: list[ModelMessage],
    *,
    attachments: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Translate PydanticAI message history into OpenAI-style chat messages.

    If ``attachments`` is provided, the *last* user message is augmented with
    multimodal content parts (images/videos as ``image_url``, documents as
    extracted text prepended to the user's text).
    """
    out: list[dict[str, Any]] = []
    # Track the index of the last UserPromptPart so we can augment only that one.
    last_user_idx: int | None = None

    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, SystemPromptPart):
                    out.append({"role": "system", "content": part.content})
                elif isinstance(part, UserPromptPart):
                    out.append({"role": "user", "content": part.content})
                    last_user_idx = len(out) - 1
                elif isinstance(part, ToolReturnPart):
                    out.append(
                        {
                            "role": "tool",
                            "tool_call_id": part.tool_call_id,
                            "content": str(part.content),
                        }
                    )
        elif isinstance(msg, ModelResponse):
            text_parts: list[str] = []
            tool_calls: list[dict[str, Any]] = []
            for part in msg.parts:
                if isinstance(part, TextPart):
                    text_parts.append(part.content)
                elif isinstance(part, ToolCallPart):
                    args = (
                        part.args
                        if isinstance(part.args, str)
                        else json.dumps(part.args or {})
                    )
                    tool_calls.append(
                        {
                            "id": part.tool_call_id,
                            "type": "function",
                            "function": {
                                "name": part.tool_name,
                                "arguments": args,
                            },
                        }
                    )
            entry: dict[str, Any] = {"role": "assistant"}
            if text_parts:
                entry["content"] = "".join(text_parts)
            if tool_calls:
                entry["tool_calls"] = tool_calls
            out.append(entry)

    # Augment the last user message with attachments if present.
    if attachments and last_user_idx is not None:
        await _augment_with_attachments(out, last_user_idx, attachments)

    return out


async def _augment_with_attachments(
    messages: list[dict[str, Any]],
    user_msg_idx: int,
    attachments: list[dict[str, Any]],
) -> None:
    """Mutate the user message at ``user_msg_idx`` to include attachment content."""
    from media_agents.agents.document_extractor import extract_text

    original_text = messages[user_msg_idx].get("content", "")
    image_parts: list[dict[str, Any]] = []
    doc_blocks: list[str] = []

    for att in attachments:
        mime = att["mime_type"]
        if mime.startswith("image/"):
            image_parts.append({
                "type": "image_url",
                "image_url": {"url": att["data_url"]},
            })
        elif mime.startswith("video/"):
            doc_blocks.append(
                f"[Attached Video: {att['filename']}]\n[End video]"
            )
        else:
            # Document — extract text
            extracted = await asyncio.to_thread(extract_text, att["data_url"], mime, att["filename"])
            doc_blocks.append(
                f"[Document: {att['filename']}]\n{extracted}\n[End document]"
            )

    # Build the enriched text (documents prepended to original message)
    enriched_text = original_text
    if doc_blocks:
        enriched_text = "\n\n".join(doc_blocks) + "\n\n" + original_text

    if image_parts:
        # Multimodal content array: images first, then text
        content: list[dict[str, Any]] = [
            *image_parts,
            {"type": "text", "text": enriched_text},
        ]
        messages[user_msg_idx]["content"] = content
    elif doc_blocks:
        # Text-only enrichment (no images) — keep as plain string
        messages[user_msg_idx]["content"] = enriched_text


def _tools_to_openai(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.parameters_json_schema,
            },
        }
        for t in tools
    ]


async def _fal_chat_function(
    messages: list[ModelMessage],
    info: AgentInfo,
) -> ModelResponse:
    return await _run_fal_chat(
        messages, info, model=_DEFAULT_MODEL, temperature=None,
        attachments=get_current_attachments(),
    )


async def _run_fal_chat(
    messages: list[ModelMessage],
    info: AgentInfo,
    *,
    model: str,
    temperature: float | None,
    attachments: list[dict[str, Any]] | None = None,
) -> ModelResponse:
    payload: dict[str, Any] = {
        "model": model,
        "messages": await _messages_to_openai(messages, attachments=attachments),
    }
    if temperature is not None:
        payload["temperature"] = temperature
    # `output_tools` carries PydanticAI's structured-output tool (for
    # `output_type=...`). Without forwarding both, structured-output agents
    # like `agent_maker` silently fall back to their error path.
    all_tools = [*info.function_tools, *info.output_tools]
    if all_tools:
        payload["tools"] = _tools_to_openai(all_tools)

    result = await fal_client.run_async(_FAL_CHAT_ENDPOINT, arguments=payload)
    choice = result["choices"][0]["message"]

    parts: list[Any] = []
    if choice.get("content"):
        parts.append(TextPart(content=choice["content"]))
    for tc in choice.get("tool_calls") or []:
        parts.append(
            ToolCallPart(
                tool_name=tc["function"]["name"],
                args=tc["function"]["arguments"],
                tool_call_id=tc["id"],
            )
        )

    return ModelResponse(parts=parts)


def make_fal_chat_model(
    model: str | None = None,
    temperature: float | None = None,
) -> FunctionModel:
    """Build a per-call FunctionModel with a chosen LLM and temperature.

    Use for team coordinators where the orchestrator-level model + temperature
    must follow the team's saved configuration rather than the global default.
    """
    chosen_model = model or _DEFAULT_MODEL

    async def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return await _run_fal_chat(
            messages, info, model=chosen_model, temperature=temperature,
            attachments=get_current_attachments(),
        )

    return FunctionModel(_fn)


# Module-level singleton — reuse the same FunctionModel for every default agent.
fal_chat_model = FunctionModel(_fal_chat_function)
