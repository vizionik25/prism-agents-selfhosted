"""Tests for TeamDagExecutor.

These tests use fake specialists: we replace `SPECIALIST_REGISTRY` entries with
stub `Agent` objects whose `.run()` is overridden to return a canned response
without touching fal.ai. Credit deduction is stubbed via monkeypatch on
`media_agents.services.credits.deduct_credits`.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

import pytest

from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.team_dag_executor import TeamDagExecutor
from media_agents.agents.team_planner import PlanNode, TeamPlan


@dataclass
class _FakeRunResult:
    output: str


class _FakeSpecialist:
    """Stand-in for a PydanticAI Agent — just defines `run()`."""

    def __init__(
        self,
        *,
        output: str = "ok",
        url: str | None = None,
        sleep: float = 0.0,
        exc: Exception | None = None,
    ):
        self._output = output
        self._url = url
        self._sleep = sleep
        self._exc = exc

    async def run(self, request: str, *, deps: OrchestratorDeps) -> _FakeRunResult:
        if self._sleep:
            await asyncio.sleep(self._sleep)
        if self._exc is not None:
            raise self._exc
        if self._url is not None:
            deps.asset_urls.append(self._url)
        return _FakeRunResult(output=self._output)


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def board_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture(autouse=True)
def _stub_credits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Short-circuit the real DB-backed credit machinery."""
    from media_agents.services import credits as credits_mod

    async def fake_deduct(user_id, cmd_type):
        return None

    async def fake_get_user(user_id):
        return {"subscriptionCredits": 10_000, "packCredits": 0}

    monkeypatch.setattr(credits_mod, "deduct_credits", fake_deduct)
    from media_agents.services import user as user_mod

    monkeypatch.setattr(user_mod, "get_user_by_id", fake_get_user)


def _register_specialist(
    monkeypatch: pytest.MonkeyPatch, cap: str, spec: _FakeSpecialist
) -> None:
    from media_agents.agents import team_dag_executor as exec_mod

    # Copy from the executor's current (possibly already-patched) view so that
    # successive calls in the same test accumulate rather than overwrite.
    registry = dict(exec_mod.SPECIALIST_REGISTRY)
    registry[cap] = spec  # type: ignore[assignment]
    monkeypatch.setattr(exec_mod, "SPECIALIST_REGISTRY", registry)


async def _drain_queue(q: asyncio.Queue[str]) -> list[str]:
    out: list[str] = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


async def test_executor_runs_single_node(monkeypatch, user_id, board_id):
    _register_specialist(
        monkeypatch,
        "text_to_image",
        _FakeSpecialist(output="done", url="https://fal.example/img.png"),
    )

    plan = TeamPlan(
        summary="s",
        nodes=[PlanNode(id="n1", member="text_to_image", request="a red dot")],
        estimated_credits=1,
    )
    deps = OrchestratorDeps(user_id=user_id, board_id=board_id, system_prompt="")
    q: asyncio.Queue[str] = asyncio.Queue()

    results = await TeamDagExecutor(plan, deps, q, max_parallel=5).run()

    assert set(results.keys()) == {"n1"}
    assert results["n1"].state == "done"
    assert results["n1"].asset_urls == ["https://fal.example/img.png"]

    events = await _drain_queue(q)
    assert any(e == "STATUS:n1:running" for e in events)
    assert any(e == "STATUS:n1:done" for e in events)
    assert any(e == "URL:n1:https://fal.example/img.png" for e in events)
    assert any(e.startswith("CREDITS:n1:") for e in events)


async def test_executor_runs_independent_nodes_concurrently(
    monkeypatch, user_id, board_id
):
    """Three independent 100ms nodes finish in <= 250ms (not 300+ ms)."""
    import time

    _register_specialist(
        monkeypatch,
        "text_to_image",
        _FakeSpecialist(output="a", url="https://fal.example/a.png", sleep=0.10),
    )
    _register_specialist(
        monkeypatch,
        "music_generation",
        _FakeSpecialist(output="b", url="https://fal.example/b.mp3", sleep=0.10),
    )
    _register_specialist(
        monkeypatch,
        "text_to_video",
        _FakeSpecialist(output="c", url="https://fal.example/c.mp4", sleep=0.10),
    )

    plan = TeamPlan(
        summary="s",
        nodes=[
            PlanNode(id="a", member="text_to_image", request="x"),
            PlanNode(id="b", member="music_generation", request="y"),
            PlanNode(id="c", member="text_to_video", request="z"),
        ],
        estimated_credits=1 + 3 + 5,
    )
    deps = OrchestratorDeps(user_id=user_id, board_id=board_id, system_prompt="")
    q: asyncio.Queue[str] = asyncio.Queue()

    t0 = time.monotonic()
    results = await TeamDagExecutor(plan, deps, q, max_parallel=5).run()
    elapsed = time.monotonic() - t0

    assert all(r.state == "done" for r in results.values())
    assert elapsed < 0.25, (
        f"independent nodes should run in parallel; took {elapsed:.3f}s"
    )


async def test_executor_waits_for_dependency(monkeypatch, user_id, board_id):
    """Downstream node starts only after its predecessor finishes."""
    import time

    start_times: dict[str, float] = {}

    class _RecordingSpec(_FakeSpecialist):
        def __init__(self, name: str, **kw):
            super().__init__(**kw)
            self._name = name

        async def run(self, request: str, *, deps: OrchestratorDeps):
            start_times[self._name] = time.monotonic()
            return await super().run(request, deps=deps)

    _register_specialist(
        monkeypatch,
        "text_to_image",
        _RecordingSpec("a", output="a", url="https://fal.example/a.png", sleep=0.10),
    )
    _register_specialist(
        monkeypatch,
        "image_to_video",
        _RecordingSpec("b", output="b", url="https://fal.example/b.mp4"),
    )

    plan = TeamPlan(
        summary="s",
        nodes=[
            PlanNode(id="a", member="text_to_image", request="x"),
            PlanNode(id="b", member="image_to_video", request="y", depends_on=["a"]),
        ],
        estimated_credits=1 + 5,
    )
    deps = OrchestratorDeps(user_id=user_id, board_id=board_id, system_prompt="")
    q: asyncio.Queue[str] = asyncio.Queue()

    await TeamDagExecutor(plan, deps, q, max_parallel=5).run()

    assert start_times["b"] - start_times["a"] >= 0.08  # >= sleep duration minus slack


async def test_executor_skips_dependents_of_failed_node(monkeypatch, user_id, board_id):
    _register_specialist(
        monkeypatch, "text_to_image", _FakeSpecialist(exc=RuntimeError("boom"))
    )
    _register_specialist(monkeypatch, "image_to_video", _FakeSpecialist(output="b"))
    _register_specialist(
        monkeypatch,
        "music_generation",
        _FakeSpecialist(output="c", url="https://fal.example/c.mp3"),
    )

    plan = TeamPlan(
        summary="s",
        nodes=[
            PlanNode(id="a", member="text_to_image", request="x"),
            PlanNode(id="b", member="image_to_video", request="y", depends_on=["a"]),
            PlanNode(id="c", member="music_generation", request="z"),  # independent
        ],
        estimated_credits=1 + 5 + 3,
    )
    deps = OrchestratorDeps(user_id=user_id, board_id=board_id, system_prompt="")
    q: asyncio.Queue[str] = asyncio.Queue()

    results = await TeamDagExecutor(plan, deps, q, max_parallel=5).run()

    assert results["a"].state == "failed"
    assert "boom" in results["a"].error
    assert results["b"].state == "skipped"
    assert "predecessor a failed" in results["b"].error
    assert results["c"].state == "done"  # independent sibling completes


async def test_executor_semaphore_bounds_in_flight(monkeypatch, user_id, board_id):
    """max_parallel=2 → at most 2 nodes are in-flight simultaneously."""
    in_flight = 0
    peak = 0
    lock = asyncio.Lock()

    class _CountingSpec(_FakeSpecialist):
        async def run(self, request: str, *, deps: OrchestratorDeps):
            nonlocal in_flight, peak
            async with lock:
                in_flight += 1
                peak = max(peak, in_flight)
            try:
                return await super().run(request, deps=deps)
            finally:
                async with lock:
                    in_flight -= 1

    _register_specialist(
        monkeypatch, "text_to_image", _CountingSpec(output="x", sleep=0.05)
    )

    plan = TeamPlan(
        summary="s",
        nodes=[
            PlanNode(id=f"n{i}", member="text_to_image", request="x") for i in range(6)
        ],
        estimated_credits=6,
    )
    deps = OrchestratorDeps(user_id=user_id, board_id=board_id, system_prompt="")
    q: asyncio.Queue[str] = asyncio.Queue()

    await TeamDagExecutor(plan, deps, q, max_parallel=2).run()

    assert peak <= 2, f"peak in-flight was {peak}, expected ≤ 2"


async def test_executor_honors_max_credits_run_cap(monkeypatch, user_id, board_id):
    _register_specialist(
        monkeypatch,
        "text_to_3d",
        _FakeSpecialist(output="ok", url="https://fal.example/m.glb"),
    )

    # 3 nodes × 10cr each = 30cr total, but cap is 15cr → only 1 should run.
    plan = TeamPlan(
        summary="s",
        nodes=[
            PlanNode(id=f"n{i}", member="text_to_3d", request="x") for i in range(3)
        ],
        estimated_credits=30,
    )
    deps = OrchestratorDeps(
        user_id=user_id,
        board_id=board_id,
        system_prompt="",
        max_credits=15,
    )
    q: asyncio.Queue[str] = asyncio.Queue()

    results = await TeamDagExecutor(plan, deps, q, max_parallel=1).run()

    done = [r for r in results.values() if r.state == "done"]
    skipped = [r for r in results.values() if r.state == "skipped"]
    assert len(done) == 1
    assert len(skipped) == 2
    assert all("run cap" in (r.error or "") for r in skipped)


async def test_executor_propagates_attachments(monkeypatch, user_id, board_id):
    attachments_captured = []

    class _AttachmentVerifyingSpec(_FakeSpecialist):
        async def run(self, request: str, *, deps: OrchestratorDeps):
            from media_agents.agents import fal_model

            attachments_captured.append(list(fal_model.get_current_attachments() or []))
            # Verify deps.attachments has the attachments
            assert deps.attachments == [
                {
                    "filename": "test.png",
                    "mime_type": "image/png",
                    "data_url": "data:...",
                }
            ]
            return await super().run(request, deps=deps)

    _register_specialist(
        monkeypatch,
        "text_to_image",
        _AttachmentVerifyingSpec(output="ok"),
    )

    plan = TeamPlan(
        summary="s",
        nodes=[PlanNode(id="n1", member="text_to_image", request="x")],
        estimated_credits=10,
    )
    deps = OrchestratorDeps(
        user_id=user_id,
        board_id=board_id,
        system_prompt="",
        attachments=[
            {"filename": "test.png", "mime_type": "image/png", "data_url": "data:..."}
        ],
    )
    q: asyncio.Queue[str] = asyncio.Queue()

    # Before running, get_current_attachments() should be None
    from media_agents.agents import fal_model

    assert fal_model.get_current_attachments() is None

    results = await TeamDagExecutor(plan, deps, q, max_parallel=1).run()

    # After running, get_current_attachments() should be cleared (None)
    assert fal_model.get_current_attachments() is None

    assert len(attachments_captured) == 1
    assert attachments_captured[0] == [
        {"filename": "test.png", "mime_type": "image/png", "data_url": "data:..."}
    ]
    assert results["n1"].state == "done"


async def test_executor_propagates_attachments_concurrently(
    monkeypatch, user_id, board_id
):
    import contextvars
    from dataclasses import dataclass
    from media_agents.agents import fal_model

    test_attachments_var = contextvars.ContextVar("test_attachments", default=[])

    @dataclass
    class TestOrchestratorDeps(OrchestratorDeps):
        @property
        def attachments(self):
            return test_attachments_var.get()

        @attachments.setter
        def attachments(self, val):
            test_attachments_var.set(val)

    captured_n1 = []
    captured_n2 = []

    class _AttachmentVerifyingSpec1(_FakeSpecialist):
        async def run(self, request: str, *, deps: OrchestratorDeps):
            # Capture before yield
            captured_n1.append(fal_model.get_current_attachments())
            await asyncio.sleep(0.05)
            # Capture after yield
            captured_n1.append(fal_model.get_current_attachments())
            return await super().run(request, deps=deps)

    class _AttachmentVerifyingSpec2(_FakeSpecialist):
        async def run(self, request: str, *, deps: OrchestratorDeps):
            # Capture before yield
            captured_n2.append(fal_model.get_current_attachments())
            await asyncio.sleep(0.05)
            # Capture after yield
            captured_n2.append(fal_model.get_current_attachments())
            return await super().run(request, deps=deps)

    _register_specialist(
        monkeypatch,
        "text_to_image",
        _AttachmentVerifyingSpec1(output="ok"),
    )
    _register_specialist(
        monkeypatch,
        "music_generation",
        _AttachmentVerifyingSpec2(output="ok"),
    )

    plan = TeamPlan(
        summary="s",
        nodes=[
            PlanNode(id="n1", member="text_to_image", request="req1"),
            PlanNode(id="n2", member="music_generation", request="req2"),
        ],
        estimated_credits=4,
    )
    deps = TestOrchestratorDeps(
        user_id=user_id,
        board_id=board_id,
        system_prompt="",
    )
    q: asyncio.Queue[str] = asyncio.Queue()

    class _CustomAttachmentsExecutor(TeamDagExecutor):
        async def _execute_node(self, node: PlanNode, cost: int) -> None:
            if node.id == "n1":
                self.deps.attachments = [
                    {
                        "filename": "n1.png",
                        "mime_type": "image/png",
                        "data_url": "n1_url",
                    }
                ]
            elif node.id == "n2":
                self.deps.attachments = [
                    {
                        "filename": "n2.png",
                        "mime_type": "image/png",
                        "data_url": "n2_url",
                    }
                ]
            await super()._execute_node(node, cost)

    # Before running, get_current_attachments() should be None
    assert fal_model.get_current_attachments() is None

    results = await _CustomAttachmentsExecutor(plan, deps, q, max_parallel=5).run()

    # After running, get_current_attachments() should be cleared (None)
    assert fal_model.get_current_attachments() is None

    assert results["n1"].state == "done"
    assert results["n2"].state == "done"

    # Verify n1 only saw n1.png
    assert len(captured_n1) == 2
    assert captured_n1[0] == [
        {"filename": "n1.png", "mime_type": "image/png", "data_url": "n1_url"}
    ]
    assert captured_n1[1] == [
        {"filename": "n1.png", "mime_type": "image/png", "data_url": "n1_url"}
    ]

    # Verify n2 only saw n2.png
    assert len(captured_n2) == 2
    assert captured_n2[0] == [
        {"filename": "n2.png", "mime_type": "image/png", "data_url": "n2_url"}
    ]
    assert captured_n2[1] == [
        {"filename": "n2.png", "mime_type": "image/png", "data_url": "n2_url"}
    ]

    # Reset attachments properly
    test_attachments_var.set([])
