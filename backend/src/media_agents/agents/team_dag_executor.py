"""DAG executor for team runs.

Reads a validated `TeamPlan` and runs each node via its specialist agent,
respecting dependencies and concurrency limits. Pushes per-node events
(STATUS/TEXT/URL/CREDITS/ERROR) onto a queue drained by orchestrator.stream().

See docs/specs/2026-04-19-parallel-agents-design.md.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Literal

from media_agents.agents.deps import OrchestratorDeps
from media_agents.agents.fal_model import (
    reset_current_attachments,
    set_current_attachments,
)
from media_agents.agents.specialist import SPECIALIST_REGISTRY
from media_agents.agents.team_planner import PlanNode, TeamPlan
from media_agents.services import credits as credits_service
from media_agents.services import user as user_service


NodeStatus = Literal["pending", "running", "done", "failed", "skipped"]


@dataclass
class NodeResult:
    state: NodeStatus = "pending"
    output_text: str = ""
    asset_urls: list[str] = field(default_factory=list)
    error: str | None = None


class TeamDagExecutor:
    """Run a TeamPlan as an asyncio DAG with a global concurrency cap."""

    def __init__(
        self,
        plan: TeamPlan,
        deps: OrchestratorDeps,
        event_queue: asyncio.Queue[str],
        max_parallel: int = 5,
    ) -> None:
        self.plan = plan
        self.deps = deps
        self.queue = event_queue
        self.semaphore = asyncio.Semaphore(max_parallel)
        self._node_events: dict[str, asyncio.Event] = {
            n.id: asyncio.Event() for n in plan.nodes
        }
        self._results: dict[str, NodeResult] = {n.id: NodeResult() for n in plan.nodes}
        self._credit_lock = asyncio.Lock()
        self._initial_balance: int | None = None

    async def run(self) -> dict[str, NodeResult]:
        tasks = [asyncio.create_task(self._run_node(n)) for n in self.plan.nodes]
        await asyncio.gather(*tasks, return_exceptions=True)
        return self._results

    async def _emit(self, chunk: str) -> None:
        await self.queue.put(chunk)

    async def _run_node(self, node: PlanNode) -> None:
        # 1) Wait for predecessors.
        for dep_id in node.depends_on:
            await self._node_events[dep_id].wait()
        # Predecessor skipped or failed → skip this node too.
        for dep_id in node.depends_on:
            if self._results[dep_id].state in ("failed", "skipped"):
                self._results[node.id].state = "skipped"
                self._results[
                    node.id
                ].error = f"predecessor {dep_id} {self._results[dep_id].state}"
                await self._emit(f"STATUS:{node.id}:skipped")
                await self._emit(
                    f"TEXT:{node.id}:↷ Skipped `{node.member}` "
                    f"(predecessor {dep_id} {self._results[dep_id].state}).\n"
                )
                self._node_events[node.id].set()
                return

        # 2) Per-run credit cap pre-check (before acquiring the semaphore —
        #    don't tie up a concurrency slot just to skip).
        cost = credits_service.cost_for_capability(node.member)
        async with self._credit_lock:
            if (
                self.deps.max_credits is not None
                and self.deps.spent_credits + cost > self.deps.max_credits
            ):
                self._results[node.id].state = "skipped"
                self._results[node.id].error = "would exceed run cap"
                await self._emit(f"STATUS:{node.id}:skipped")
                await self._emit(
                    f"TEXT:{node.id}:⛔ Skipped `{node.member}` ({cost} credits) — "
                    f"would exceed {self.deps.max_credits}-credit run cap.\n"
                )
                self._node_events[node.id].set()
                return

        # 3) Acquire the global semaphore.
        async with self.semaphore:
            await self._execute_node(node, cost)
        self._node_events[node.id].set()

    async def _execute_node(self, node: PlanNode, cost: int) -> None:
        specialist = SPECIALIST_REGISTRY.get(node.member)
        if specialist is None:
            # Validator should have caught this, but belt-and-suspenders.
            self._results[node.id].state = "failed"
            self._results[node.id].error = f"unknown member {node.member}"
            await self._emit(f"STATUS:{node.id}:failed")
            await self._emit(f"TEXT:{node.id}:✗ unknown member `{node.member}`\n")
            return

        cmd_type = credits_service.command_for_capability(node.member)

        # Single atomic region for balance check + deduct + spent_credits
        # mutation. Serializes concurrent nodes within the same run so we
        # can't over-deduct when two tasks race past the balance check.
        async with self._credit_lock:
            if self._initial_balance is None:
                user = await user_service.get_user_by_id(self.deps.user_id)
                self._initial_balance = (
                    (user.get("subscriptionCredits") or 0)
                    + (user.get("packCredits") or 0)
                    if user
                    else 0
                )
            if self._initial_balance - self.deps.spent_credits < cost:
                self._results[node.id].state = "skipped"
                self._results[node.id].error = "insufficient credits"
                await self._emit(f"STATUS:{node.id}:skipped")
                await self._emit(
                    f"TEXT:{node.id}:⛔ Skipped `{node.member}` — "
                    f"needs {cost} credits, balance is {self._initial_balance - self.deps.spent_credits}.\n"
                )
                return
            await credits_service.deduct_credits(self.deps.user_id, cmd_type)
            self.deps.spent_credits += cost
            spent_now = self.deps.spent_credits
        await self._emit(f"CREDITS:{node.id}:{spent_now}")

        self._results[node.id].state = "running"
        await self._emit(f"STATUS:{node.id}:running")
        await self._emit(
            f"TEXT:{node.id}:→ Delegating to `{node.member}` ({cost} credits) — "
            f"{_preview(node.request)}\n"
        )

        sub_deps = OrchestratorDeps(
            user_id=self.deps.user_id,
            board_id=self.deps.board_id,
            system_prompt="",
            attachments=list(self.deps.attachments),
        )
        token = set_current_attachments(sub_deps.attachments)
        try:
            result = await specialist.run(node.request, deps=sub_deps)
        except Exception as e:
            self._results[node.id].state = "failed"
            self._results[node.id].error = str(e)
            await self._emit(f"STATUS:{node.id}:failed")
            await self._emit(f"TEXT:{node.id}:✗ `{node.member}` failed: {e}\n")
            return
        finally:
            reset_current_attachments(token)

        self._results[node.id].output_text = result.output or ""
        self._results[node.id].asset_urls = list(sub_deps.asset_urls)
        # Bubble up to the orchestrator deps so the generation row ends with
        # the combined asset list.
        self.deps.asset_urls.extend(sub_deps.asset_urls)

        for url in sub_deps.asset_urls:
            await self._emit(f"URL:{node.id}:{url}")
        self._results[node.id].state = "done"
        await self._emit(f"STATUS:{node.id}:done")
        await self._emit(f"TEXT:{node.id}:✓ `{node.member}` done.\n")


def _preview(request: str, limit: int = 140) -> str:
    return request if len(request) <= limit else request[: limit - 1] + "…"
