import base64
import json
import logging
import time
import uuid

from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional

from media_agents.services import agent as agent_service
from media_agents.services import board as board_service
from media_agents.services import generation as generation_service
from media_agents.services import team as team_service
from media_agents.services import user as user_service
from media_agents.services.credits import (
    CREDIT_COSTS,
    check_credits,
    deduct_credits,
    get_command_type,
)
from media_agents.agents.orchestrator import AgentOrchestrator
from media_agents.analytics import analytics
from media_agents.analytics.events import (
    CREDITS_DEPLETED,
    GENERATION_COMPLETED,
    GENERATION_STARTED,
)
from media_agents.analytics.traits import credit_traits

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str
    content: str


ALLOWED_MIME_TYPES = {
    # Images
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
    # Videos
    "video/mp4", "video/webm", "video/quicktime", "video/x-msvideo",
    # Documents
    "application/pdf", "text/plain", "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Per-type size limits in bytes
_SIZE_LIMITS = {
    "image": 20 * 1024 * 1024,     # 20 MB
    "video": 50 * 1024 * 1024,     # 50 MB
    "document": 10 * 1024 * 1024,  # 10 MB
}


def _size_category(mime_type: str) -> str:
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("video/"):
        return "video"
    return "document"


class ChatAttachment(BaseModel):
    filename: str
    mime_type: str
    data_url: str  # "data:<mime>;base64,<content>"


def validate_attachments(attachments: list[ChatAttachment]) -> None:
    """Validate attachment count, MIME types, and decoded sizes. Raises HTTPException on failure."""
    if len(attachments) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 attachments per message")

    for att in attachments:
        # Sanitize MIME type (handling parameters like charset)
        mime = att.mime_type.split(";")[0].strip().lower()
        if mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {att.mime_type}",
            )

        category = _size_category(mime)
        limit = _SIZE_LIMITS[category]
        limit_mb = limit / (1024 * 1024)
        limit_str = f"{limit_mb:.0f}" if limit_mb.is_integer() else f"{limit_mb:.1f}"

        if "," not in att.data_url:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 data for {att.filename}",
            )
        _, _, encoded = att.data_url.partition(",")

        # Early size check (estimate decoded size)
        padding = 0
        if encoded.endswith("=="):
            padding = 2
        elif encoded.endswith("="):
            padding = 1
        approx_size = (len(encoded) * 3) // 4 - padding

        if approx_size > limit:
            actual_mb = approx_size / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"File {att.filename} exceeds {limit_str}MB limit for {category}s ({actual_mb:.1f}MB)",
            )

        # Decode strictly to check actual size
        try:
            raw = base64.b64decode(encoded, validate=True)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 data for {att.filename}",
            )

        if len(raw) > limit:
            actual_mb = len(raw) / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"File {att.filename} exceeds {limit_str}MB limit for {category}s ({actual_mb:.1f}MB)",
            )


class ChatRequest(BaseModel):
    board_id: uuid.UUID
    message: str
    agent_id: Optional[uuid.UUID] = None
    capability: Optional[str] = None  # run a pre-configured specialist directly
    team_id: Optional[uuid.UUID] = (
        None  # run a saved Team with full orchestrator config
    )
    max_credits_per_run: Optional[int] = (
        None  # per-call cap; overrides team's saved cap
    )
    history: list[ChatMessage] = []
    attachments: list[ChatAttachment] = []



def _strip_node_scope(payload: str) -> tuple[str | None, str]:
    """Split a prefix-tagged payload into (node_id, rest).

    DAG-scoped events carry ``<node_id>:<content>`` in the payload after the
    outer prefix (e.g. ``TEXT:n1:hello``). Returns ``(node_id, content)`` for
    scoped payloads, ``(None, payload)`` otherwise. A ``:`` inside a URL after
    the scheme is NOT a scope — scopes are always a short identifier before
    the first colon, followed by more content.

    Conservative rule: a scope is present only if the first colon-split yields
    a head that looks like a node id (alphanumeric + underscore + dash, no
    slashes or dots) AND the remainder does not start with ``/`` (which would
    indicate a URL scheme like ``https://``).
    """
    colon = payload.find(":")
    if colon <= 0:
        return None, payload
    head = payload[:colon]
    # A node id contains only [A-Za-z0-9_-]. Strip the allowed punctuation
    # before the isalnum check.
    if not head.replace("_", "").replace("-", "").isalnum():
        return None, payload
    rest = payload[colon + 1 :]
    # URLs have '/' immediately after '<scheme>:' — treat as NOT scoped.
    if rest.startswith("/"):
        return None, payload
    return head, rest


def _infer_result_type(message: str, urls: list[str]) -> str:
    msg = message.lower().strip()
    if msg.startswith("/image "):
        return "image"
    if msg.startswith("/video ") or msg.startswith("/motion "):
        return "video"
    if msg.startswith("/music "):
        return "audio"
    if any(
        msg.startswith(p) for p in ("/3d ", "/image-to-3d ", "/remesh ", "/retexture ")
    ):
        return "model_3d"
    if any(msg.startswith(p) for p in ("/vision ", "/analyze-video ")):
        return "text"
    if urls:
        return "image"
    return "text"


async def stream_chat_events(request: ChatRequest, user_id: uuid.UUID):
    user = await user_service.get_user_by_id(user_id)
    if user is None:
        yield {"event": "error", "data": "User not found"}
        return

    command_type = get_command_type(request.message)
    user_email = user.get("email")
    try:
        check_credits(user, command_type)
    except Exception as e:
        if isinstance(e, HTTPException):
            detail = e.detail if isinstance(e.detail, dict) else {}
            if detail.get("code") == "insufficient_credits":
                analytics.capture(
                    user_id=str(user_id),
                    event=CREDITS_DEPLETED,
                    email=user_email,
                    properties={
                        "attempted_command": command_type,
                        "required_credits": detail.get("required") or 0,
                        "available_credits": detail.get("available") or 0,
                    },
                )
            yield {"event": "error", "data": json.dumps(e.detail)}
        else:
            yield {"event": "error", "data": str(e)}
        return

    board = await board_service.get_board_by_id(request.board_id, user_id)
    if board is None:
        yield {"event": "error", "data": "Board not found"}
        return

    agent = None
    if request.agent_id:
        agent = await agent_service.get_agent_by_id(request.agent_id, user_id)
        if agent is None:
            yield {"event": "error", "data": "Agent not found"}
            return

    team = None
    team_member_agents: list[dict] = []
    if request.team_id and not agent:
        team = await team_service.get_team_by_id(request.team_id, user_id)
        if team is None:
            yield {"event": "error", "data": "Team not found"}
            return
        member_ids = set((team.get("members") or {}).get("agent_ids") or [])
        if member_ids:
            board_agents = await agent_service.get_agents_by_user(user_id)
            team_member_agents = [a for a in board_agents if a["id"] in member_ids]

    generation = await generation_service.create_generation(
        user_id, request.board_id, request.message, request.agent_id
    )
    gen_id = uuid.UUID(generation["id"])

    started_at_ms = time.monotonic()
    analytics.capture(
        user_id=str(user_id),
        event=GENERATION_STARTED,
        email=user_email,
        properties={
            "generation_id": str(gen_id),
            "board_id": str(request.board_id),
            "agent_id": str(request.agent_id) if request.agent_id else None,
            "team_id": str(request.team_id) if request.team_id else None,
            "parent_generation_id": None,
            "command_type": command_type,
            "is_slash_command": command_type != "chat",
            "mode": "team" if request.team_id else "single",
            "credit_cost": CREDIT_COSTS.get(command_type, 1),
            "prompt_length": len(request.message),
        },
    )

    yield {"event": "generation_start", "data": str(gen_id)}

    try:
        orchestrator = AgentOrchestrator(user_id=user_id, board_id=request.board_id)

        if agent:
            orchestrator.set_custom_agent(
                agent["systemPrompt"], agent.get("config", {})
            )
        elif team:
            orchestrator.set_team_from_config(
                team,
                team_member_agents,
                max_credits_override=request.max_credits_per_run,
            )
        elif request.capability:
            # Route directly to a pre-configured specialist via its capability key.
            orchestrator.set_custom_agent(
                system_prompt="",  # specialist uses its own static instructions
                config={"capability": request.capability},
            )

        full_response = ""
        urls: list[str] = []
        history_dicts = [
            {"role": m.role, "content": m.content} for m in request.history
        ]
        attachments_list = getattr(request, "attachments", None) or []
        attachment_dicts = [
            {"filename": a.filename, "mime_type": a.mime_type, "data_url": a.data_url}
            for a in attachments_list
        ]

        async for chunk in orchestrator.stream(
            request.message, history_dicts, attachments=attachment_dicts
        ):
            if chunk.startswith("PLAN:"):
                # Plan peek — one per team DAG run. UI renders this as a plan
                # card with per-node lanes.
                yield {"event": "plan", "data": chunk[5:]}
            elif chunk.startswith("TEXT:"):
                payload = chunk[5:]
                # Node-scoped text (``n1:...``) gets its scope stripped before
                # accumulating into ``full_response`` so the persisted
                # ``metadata["text"]`` stays clean. The full scoped payload is
                # still forwarded to the client for per-lane rendering.
                _, text_content = _strip_node_scope(payload)
                full_response += text_content
                yield {"event": "message", "data": payload}
            elif chunk.startswith("URL:"):
                payload = chunk[4:]
                # Strip node scope before appending so ``result_url`` and
                # variant rows store clean URLs. Forward the scoped payload
                # on the wire so the UI can route URLs into the right lane.
                _, url_clean = _strip_node_scope(payload)
                urls.append(url_clean)
                yield {"event": "url", "data": payload}
            elif chunk.startswith("CREDITS:"):
                # Per-delegation credit deduction inside team coordinator —
                # surface as a dedicated event so the client can update spend
                # display without polluting the generation status enum.
                yield {"event": "credits", "data": chunk[8:]}
            elif chunk.startswith("STATUS:"):
                status_str = chunk[7:]
                # Node-scoped status (e.g. ``n1:running``) MUST NOT update the
                # Generation row — the Prisma ``GenerationStatus`` enum only
                # accepts run-level values (PENDING/PROCESSING/COMPLETED/FAILED).
                # Only persist when the payload has no node scope.
                node_scope, _ = _strip_node_scope(status_str)
                if node_scope is None:
                    await generation_service.update_generation(
                        gen_id, status=status_str.upper()
                    )
                yield {"event": "status", "data": status_str}
            elif chunk.startswith("ERROR:"):
                error = chunk[6:]
                await generation_service.update_generation(gen_id, status="FAILED")
                analytics.capture(
                    user_id=str(user_id),
                    event=GENERATION_COMPLETED,
                    email=user_email,
                    properties={
                        "generation_id": str(gen_id),
                        "board_id": str(request.board_id),
                        "agent_id": str(request.agent_id) if request.agent_id else None,
                        "team_id": str(request.team_id) if request.team_id else None,
                        "command_type": command_type,
                        "status": "failed",
                        "duration_ms": int((time.monotonic() - started_at_ms) * 1000),
                        "credits_deducted": 0,
                        "result_type": None,
                        "variants_count": 0,
                        "error_type": "orchestrator_error",
                        "error_code": None,
                    },
                )
                yield {"event": "error", "data": error}
                return

        result_type = _infer_result_type(request.message, urls)
        meta: dict = {"text": full_response, "response_length": len(full_response)}
        attachments_list = getattr(request, "attachments", None) or []
        if attachments_list:
            meta["attachments"] = [a.filename for a in attachments_list]
        await generation_service.update_generation(
            gen_id,
            status="COMPLETED",
            result_url=urls[0] if urls else None,
            result_type=result_type,
            metadata=meta,
        )

    except Exception as e:
        await generation_service.update_generation(gen_id, status="FAILED")
        analytics.capture(
            user_id=str(user_id),
            event=GENERATION_COMPLETED,
            email=user_email,
            properties={
                "generation_id": str(gen_id),
                "board_id": str(request.board_id),
                "agent_id": str(request.agent_id) if request.agent_id else None,
                "team_id": str(request.team_id) if request.team_id else None,
                "command_type": command_type,
                "status": "failed",
                "duration_ms": int((time.monotonic() - started_at_ms) * 1000),
                "credits_deducted": 0,
                "result_type": None,
                "variants_count": 0,
                "error_type": "internal",
                "error_code": type(e).__name__,
            },
        )
        yield {"event": "error", "data": str(e)}
        yield {"event": "generation_end", "data": ""}
        return

    # Variants are best-effort — a persistence failure here must not flip the
    # generation back to FAILED after we've already told the client it succeeded.
    if len(urls) > 1:
        variants_data = [
            {
                "variant_index": i,
                "result_url": extra_url,
                "result_type": result_type,
            }
            for i, extra_url in enumerate(urls[1:], start=1)
        ]
        try:
            await generation_service.add_variants(gen_id, variants_data)
        except Exception:
            logger.exception(
                "Bulk insert failed for generation %s, falling back to one-by-one",
                gen_id,
            )
            for i, extra_url in enumerate(urls[1:], start=1):
                try:
                    await generation_service.add_variant(
                        gen_id,
                        variant_index=i,
                        result_url=extra_url,
                        result_type=result_type,
                    )
                except Exception:
                    logger.exception(
                        "failed to persist variant %d for generation %s", i, gen_id
                    )

    # Team DAG runs deduct per-node inside the executor; skip the trailing
    # flat deduction to avoid double-charging.
    credits_deducted = 0
    if request.team_id is None:
        await deduct_credits(user_id, command_type)
        credits_deducted = CREDIT_COSTS.get(command_type, 0)

    refreshed = await user_service.get_user_by_id(user_id)
    # PostHog $set_once only writes on the first event per distinct_id, so it's
    # safe to send this every time — no need to query whether it's the first run.
    from datetime import datetime, timezone

    set_once = {"first_generation_at": datetime.now(timezone.utc).isoformat()}

    analytics.capture(
        user_id=str(user_id),
        event=GENERATION_COMPLETED,
        email=user_email,
        properties={
            "generation_id": str(gen_id),
            "board_id": str(request.board_id),
            "agent_id": str(request.agent_id) if request.agent_id else None,
            "team_id": str(request.team_id) if request.team_id else None,
            "command_type": command_type,
            "status": "succeeded",
            "duration_ms": int((time.monotonic() - started_at_ms) * 1000),
            "credits_deducted": credits_deducted,
            "result_type": result_type,
            "variants_count": max(0, len(urls) - 1),
            "error_type": None,
            "error_code": None,
        },
        set_traits=credit_traits(refreshed) if refreshed else None,
        set_once_traits=set_once,
    )
    yield {"event": "generation_end", "data": ""}
