"""Tests for the chat router's pure helpers.

These guard the result-type inference rules and are the regression net for the
"`/image` URL gets misclassified as text" fix from the audit.
"""

from __future__ import annotations

import uuid as _uuid
from types import SimpleNamespace

import pytest

from media_agents.services.chat import _infer_result_type, _strip_node_scope


@pytest.mark.parametrize(
    "message, urls, expected",
    [
        ("/image a sunset", [], "image"),
        ("/IMAGE a sunset", [], "image"),
        ("/video a city", [], "video"),
        ("hello there", [], "text"),
        # Regression: orchestrator yielded URLs but command wasn't /image|/video
        # (e.g. a custom-agent tool call). Type must NOT be "text" if URLs exist.
        ("freeform message", ["https://example.com/x.png"], "image"),
        # Plain text generation with no URLs stays as "text".
        ("freeform message", [], "text"),
    ],
)
def test_infer_result_type(message: str, urls: list[str], expected: str) -> None:
    assert _infer_result_type(message, urls) == expected


@pytest.mark.parametrize(
    "payload, expected",
    [
        # Unscoped payloads (no scope — return (None, payload)).
        ("hello world", (None, "hello world")),
        ("processing", (None, "processing")),
        ("completed", (None, "completed")),
        # URL with scheme is NOT scoped.
        ("https://fal.example/image.png", (None, "https://fal.example/image.png")),
        ("http://example.com/a.mp4", (None, "http://example.com/a.mp4")),
        # Scoped payloads.
        ("n1:running", ("n1", "running")),
        ("n1:done", ("n1", "done")),
        ("n42:some text content here", ("n42", "some text content here")),
        ("n1:https://fal.example/image.png", ("n1", "https://fal.example/image.png")),
        # Node IDs can contain dash/underscore.
        ("node_1:text", ("node_1", "text")),
        ("node-2:text", ("node-2", "text")),
        # Empty head segment (leading colon) is not a scope.
        (":foo", (None, ":foo")),
    ],
)
def test_strip_node_scope(payload: str, expected: tuple[str | None, str]) -> None:
    assert _strip_node_scope(payload) == expected


async def test_chat_router_plan_event_and_scoped_events_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Router must:
    - Forward ``PLAN:`` as SSE ``plan`` event.
    - Forward node-scoped ``STATUS`` as SSE ``status`` WITHOUT calling
      ``update_generation`` for the scoped payload.
    - Strip node-scope from URL/TEXT before persisting, but forward the
      full payload to the client on the wire.
    """
@pytest.fixture
async def _chat_stream_results(monkeypatch: pytest.MonkeyPatch) -> dict:
    from media_agents.services import chat as chat_mod
    from media_agents.services import board as board_mod
    from media_agents.services import generation as generation_mod
    from media_agents.services import user as user_mod

    # Stubs for the services the generator touches. None of these must hit
    # Prisma — all async callables return plain dicts.
    async def fake_get_user(user_id):  # type: ignore[no-untyped-def]
        return {
            "id": str(user_id),
            "subscriptionCredits": 100,
            "packCredits": 0,
        }

    async def fake_get_board(board_id, user_id):  # type: ignore[no-untyped-def]
        return {"id": str(board_id)}

    async def fake_create_gen(user_id, board_id, message, agent_id):  # type: ignore[no-untyped-def]
        return {"id": str(_uuid.uuid4())}

    status_updates: list[str] = []
    update_calls: list[dict] = []

    async def fake_update_gen(gen_id, **kwargs):  # type: ignore[no-untyped-def]
        update_calls.append(kwargs)
        if "status" in kwargs:
            status_updates.append(kwargs["status"])

    async def fake_add_variant(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return None

    async def fake_deduct(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return None

    monkeypatch.setattr(user_mod, "get_user_by_id", fake_get_user)
    monkeypatch.setattr(board_mod, "get_board_by_id", fake_get_board)
    monkeypatch.setattr(generation_mod, "create_generation", fake_create_gen)
    monkeypatch.setattr(generation_mod, "update_generation", fake_update_gen)
    monkeypatch.setattr(generation_mod, "add_variant", fake_add_variant)
    monkeypatch.setattr(chat_mod, "deduct_credits", fake_deduct)

    class _FakeOrch:
        def __init__(self, user_id, board_id):  # type: ignore[no-untyped-def]
            pass

        def set_team_from_config(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            pass

        def set_custom_agent(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            pass

        def set_team_agents(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            pass

        async def stream(self, _msg, _history, *args, **kwargs):  # type: ignore[no-untyped-def]
            yield "STATUS:processing"
            yield 'PLAN:{"summary":"x","nodes":[],"estimated_credits":0}'
            yield "STATUS:n1:running"
            yield "URL:n1:https://fal.example/a.png"
            yield "TEXT:n1:progress chatter"
            yield "STATUS:n1:done"
            yield "TEXT:final synthesis"
            yield "STATUS:completed"

    monkeypatch.setattr(chat_mod, "AgentOrchestrator", _FakeOrch)

    req = SimpleNamespace(
        board_id=_uuid.uuid4(),
        message="hi",
        history=[],
        agent_id=None,
        capability=None,
        team_id=None,
        max_credits_per_run=None,
        team_mode=False,
        team_agent_ids=[],
        team_capabilities=[],
    )

    events: list[dict] = []
    async for evt in chat_mod.stream_chat_events(req, _uuid.uuid4()):
        events.append(evt)

    return {
        "events": events,
        "status_updates": status_updates,
        "update_calls": update_calls,
    }


async def test_chat_router_forwards_plan_event(_chat_stream_results: dict) -> None:
    events = _chat_stream_results["events"]
    plan_events = [e for e in events if e["event"] == "plan"]
    assert len(plan_events) == 1
    assert '"summary":"x"' in plan_events[0]["data"]


async def test_chat_router_handles_status_events(_chat_stream_results: dict) -> None:
    events = _chat_stream_results["events"]
    status_updates = _chat_stream_results["status_updates"]

    status_events = [e for e in events if e["event"] == "status"]

    # Scoped status events forwarded with the full payload on the wire.
    assert any(e["data"] == "n1:running" for e in status_events)
    assert any(e["data"] == "n1:done" for e in status_events)

    # Run-level statuses forwarded too.
    assert any(e["data"] == "processing" for e in status_events)
    assert any(e["data"] == "completed" for e in status_events)

    # Only run-level statuses were persisted to the Generation row.
    assert "N1:RUNNING" not in status_updates
    assert "N1:DONE" not in status_updates
    assert "PROCESSING" in status_updates
    assert "COMPLETED" in status_updates


async def test_chat_router_forwards_url_events(_chat_stream_results: dict) -> None:
    events = _chat_stream_results["events"]
    url_events = [e for e in events if e["event"] == "url"]
    assert any(e["data"] == "n1:https://fal.example/a.png" for e in url_events)

    # Scoped URL forwarded on the wire with scope intact.
    assert any(e["data"] == "n1:https://fal.example/a.png" for e in url_events)


async def test_chat_router_forwards_text_events(_chat_stream_results: dict) -> None:
    events = _chat_stream_results["events"]
    msg_events = [e for e in events if e["event"] == "message"]

    # Scoped + unscoped text events forwarded with their full payloads.
    assert any(e["data"] == "n1:progress chatter" for e in msg_events)
    assert any(e["data"] == "final synthesis" for e in msg_events)


async def test_chat_router_cleans_terminal_persistence(
    _chat_stream_results: dict,
) -> None:
    update_calls = _chat_stream_results["update_calls"]

    terminal = next(
        c for c in update_calls if c.get("status") == "COMPLETED" and "metadata" in c
    )

    # result_url stripped of node scope.
    assert terminal.get("result_url") == "https://fal.example/a.png"
    assert "n1:" not in (terminal.get("result_url") or "")

    # metadata.text stripped of node scope.
    metadata = terminal.get("metadata", {})
    assert "n1:" not in metadata.get("text", "")

    # The clean synthesis text AND the scope-stripped "progress chatter" both accumulate.
    assert "progress chatter" in metadata.get("text", "")
    assert "final synthesis" in metadata.get("text", "")


async def test_chat_router_skips_trailing_deduct_for_team_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Team DAG runs deduct per-node inside the executor; the router must
    NOT fire the trailing flat deduction or the user is over-charged.

    Covers the billing-bug fix surfaced in the feat/teams-orchestrator
    end-to-end review: without the guard, every team run paid twice.
    """
    from media_agents.services import chat as chat_mod
    from media_agents.services import agent as agent_mod
    from media_agents.services import board as board_mod
    from media_agents.services import generation as generation_mod
    from media_agents.services import team as team_mod
    from media_agents.services import user as user_mod

    deduct_calls: list[tuple] = []

    async def fake_deduct(user_id, cmd_type):  # type: ignore[no-untyped-def]
        deduct_calls.append((user_id, cmd_type))

    async def fake_get_user(user_id):  # type: ignore[no-untyped-def]
        return {
            "id": str(user_id),
            "subscriptionCredits": 100,
            "packCredits": 0,
        }

    async def fake_get_board(board_id, user_id):  # type: ignore[no-untyped-def]
        return {"id": str(board_id)}

    async def fake_create_gen(user_id, board_id, message, agent_id):  # type: ignore[no-untyped-def]
        return {"id": str(_uuid.uuid4())}

    async def fake_update_gen(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return None

    async def fake_add_variant(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return None

    async def fake_get_team(team_id, user_id):  # type: ignore[no-untyped-def]
        return {
            "id": str(team_id),
            "name": "T",
            "orchestrator": {},
            "members": {"capabilities": [], "agent_ids": []},
        }

    async def fake_get_agents_by_user(user_id):  # type: ignore[no-untyped-def]
        return []

    monkeypatch.setattr(user_mod, "get_user_by_id", fake_get_user)
    monkeypatch.setattr(board_mod, "get_board_by_id", fake_get_board)
    monkeypatch.setattr(generation_mod, "create_generation", fake_create_gen)
    monkeypatch.setattr(generation_mod, "update_generation", fake_update_gen)
    monkeypatch.setattr(generation_mod, "add_variant", fake_add_variant)
    monkeypatch.setattr(team_mod, "get_team_by_id", fake_get_team)
    monkeypatch.setattr(agent_mod, "get_agents_by_user", fake_get_agents_by_user)
    monkeypatch.setattr(chat_mod, "deduct_credits", fake_deduct)

    class _FakeOrch:
        def __init__(self, user_id, board_id):  # type: ignore[no-untyped-def]
            pass

        def set_team_from_config(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            pass

        def set_custom_agent(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            pass

        def set_team_agents(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            pass

        async def stream(self, _msg, _history, *args, **kwargs):  # type: ignore[no-untyped-def]
            yield "STATUS:processing"
            yield "STATUS:completed"

    monkeypatch.setattr(chat_mod, "AgentOrchestrator", _FakeOrch)

    # Case 1: team_id set -> trailing deduct MUST NOT fire.
    req_team = SimpleNamespace(
        board_id=_uuid.uuid4(),
        message="hi",
        history=[],
        agent_id=None,
        capability=None,
        team_id=_uuid.uuid4(),
        max_credits_per_run=None,
        team_mode=False,
        team_agent_ids=[],
        team_capabilities=[],
    )
    async for _evt in chat_mod.stream_chat_events(req_team, _uuid.uuid4()):
        pass
    assert deduct_calls == [], (
        f"team run should not trigger trailing deduct; got {deduct_calls}"
    )

    # Case 2: no team_id -> trailing deduct MUST fire (single-agent path).
    deduct_calls.clear()
    req_single = SimpleNamespace(
        board_id=_uuid.uuid4(),
        message="hi",
        history=[],
        agent_id=None,
        capability=None,
        team_id=None,
        max_credits_per_run=None,
        team_mode=False,
        team_agent_ids=[],
        team_capabilities=[],
    )
    async for _evt in chat_mod.stream_chat_events(req_single, _uuid.uuid4()):
        pass
    assert len(deduct_calls) == 1, (
        f"single-agent run should deduct once; got {deduct_calls}"
    )
    assert deduct_calls[0][1] == "chat"


async def test_chat_router_endpoint_validate_attachments(monkeypatch):
    from media_agents.routers.chat import chat_stream
    from media_agents.services.chat import ChatRequest, ChatAttachment
    from fastapi import HTTPException

    # 1. Invalid attachment (e.g., unsupported mime type)
    bad_att = ChatAttachment(
        filename="test.exe",
        mime_type="application/octet-stream",
        data_url="data:application/octet-stream;base64,YWJj"
    )
    req = ChatRequest(
        board_id=_uuid.uuid4(),
        message="hi",
        history=[],
        attachments=[bad_att]
    )

    # Mock DB ensure helpers called in DEMO_MODE so the test doesn't crash on DB queries
    monkeypatch.setattr("media_agents.routers.chat.DEMO_MODE", False)

    with pytest.raises(HTTPException) as excinfo:
        await chat_stream(
            request=req,
            current_user={"id": str(_uuid.uuid4())}
        )
    assert excinfo.value.status_code == 400
    assert "Unsupported file type" in excinfo.value.detail
