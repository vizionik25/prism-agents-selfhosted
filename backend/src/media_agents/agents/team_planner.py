"""Team execution planner.

Produces a validated `TeamPlan` (a DAG of specialist calls) from a user
message and a team's roster. The planner makes one LLM call; all structural
validation is deterministic Python that runs after the call and before any
fal.ai work.

See docs/specs/2026-04-19-parallel-agents-design.md.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from media_agents.agents.fal_model import fal_chat_model, make_fal_chat_model
from media_agents.agents.specialist import SPECIALIST_REGISTRY
from media_agents.services.credits import cost_for_capability


class PlanNode(BaseModel):
    id: str = Field(
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Stable id within this plan, e.g. 'n1'. Must be "
        "alphanumeric plus underscore/dash — the executor embeds it in "
        "wire events via <prefix>:<id>:<payload>.",
    )
    member: str = Field(
        description="Specialist capability key (must exist in SPECIALIST_REGISTRY)."
    )
    request: str = Field(
        description="Self-contained instruction for the specialist. Include all "
        "context — specialists cannot see the conversation history."
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Ids of predecessor nodes. Empty = ready at t=0.",
    )
    rationale: str | None = Field(
        default=None,
        description="Optional one-line explanation shown in the UI plan peek.",
    )


class TeamPlan(BaseModel):
    summary: str = Field(description="One-sentence human description of the plan.")
    nodes: list[PlanNode]
    estimated_credits: int = Field(
        description="Sum of cost_for_capability(member) across all nodes."
    )


MAX_DAG_NODES = 12


class PlanValidationError(ValueError):
    """Raised when a TeamPlan fails structural or budget checks."""


def validate_plan(
    plan: TeamPlan,
    *,
    user_balance: int,
    max_credits: int | None,
) -> None:
    """Raise PlanValidationError if the plan is unsafe to execute.

    Checks (in order):
      1. Non-empty.
      2. Node count <= MAX_DAG_NODES.
      3. Every `member` is a known specialist capability.
      4. Every `depends_on` id references an earlier node (catches cycles
         and forward dependencies in one pass).
      5. `estimated_credits` equals the computed sum — no lying.
      6. `estimated_credits` fits inside both the user balance and the
         run cap (if any).
    """
    if not plan.nodes:
        raise PlanValidationError("empty plan")
    if len(plan.nodes) > MAX_DAG_NODES:
        raise PlanValidationError(
            f"too many nodes ({len(plan.nodes)} > {MAX_DAG_NODES})"
        )

    seen: set[str] = set()
    all_node_ids: set[str] | None = None
    computed_cost = 0
    for node in plan.nodes:
        if node.id in seen:
            raise PlanValidationError(f"duplicate node id: {node.id!r}")
        if node.member not in SPECIALIST_REGISTRY:
            raise PlanValidationError(f"unknown member: {node.member!r}")
        for dep in node.depends_on:
            if dep == node.id:
                raise PlanValidationError(f"self-dependency on {node.id!r}")
            if dep not in seen:
                if all_node_ids is None:
                    all_node_ids = {n.id for n in plan.nodes}
                if dep in all_node_ids:
                    raise PlanValidationError(
                        f"forward dependency: node {node.id!r} depends on {dep!r} "
                        "which is declared later"
                    )
                raise PlanValidationError(
                    f"unknown dependency: node {node.id!r} depends on {dep!r}"
                )
        seen.add(node.id)
        computed_cost += cost_for_capability(node.member)

    if plan.estimated_credits != computed_cost:
        raise PlanValidationError(
            f"estimated_credits mismatch: plan says {plan.estimated_credits}, "
            f"computed {computed_cost}"
        )

    if plan.estimated_credits > user_balance:
        raise PlanValidationError(
            f"insufficient credits: plan needs {plan.estimated_credits}, "
            f"user has {user_balance}"
        )
    if max_credits is not None and plan.estimated_credits > max_credits:
        raise PlanValidationError(
            f"exceeds run cap: plan needs {plan.estimated_credits}, "
            f"run cap is {max_credits}"
        )


PLANNER_SYSTEM_PROMPT = """You are a planner for a team of media-generation specialists.

Your one job: turn a user request into a TeamPlan — a directed acyclic graph of
specialist calls. Emit the plan via the structured output; emit nothing else.

Rules:
  • Use `depends_on` ONLY when a node literally needs another node's output URL
    as input (e.g. image_to_video needs the URL produced by text_to_image).
  • For independent outputs (logo + jingle + video), leave `depends_on` empty
    on each — the executor runs them concurrently.
  • Give each node a self-contained `request` — specialists never see the
    conversation history.
  • `estimated_credits` must equal the exact sum of per-capability costs.
  • Use only member keys that appear in the roster below.
  • Keep plans minimal. Do not add nodes that weren't asked for.
"""


# Module-level planner agent — the model is overridden per call via
# `make_fal_chat_model(...)` when a custom model/temperature is needed.
planner_agent: Agent[None, TeamPlan] = Agent(
    fal_chat_model,
    deps_type=None,
    output_type=TeamPlan,
    instructions=PLANNER_SYSTEM_PROMPT,
)


def _format_planner_prompt(
    *,
    message: str,
    team_name: str,
    capabilities: list[str],
    custom_agents: list[dict[str, Any]],
    routing_strategy: str,
) -> str:
    roster_lines: list[str] = []
    for cap in capabilities:
        if cap in SPECIALIST_REGISTRY:
            roster_lines.append(f"  • {cap} ({cost_for_capability(cap)} credits)")
    for ca in custom_agents:
        cap = (ca.get("config") or {}).get("capability")
        if cap and cap in SPECIALIST_REGISTRY:
            name = ca.get("name", "custom")
            desc = ca.get("description") or ""
            roster_lines.append(
                f"  • {cap} ({cost_for_capability(cap)} credits) — custom: {name} — {desc}"
            )
    roster = "\n".join(roster_lines) if roster_lines else "  (no members)"

    return (
        f"Team: {team_name}\n"
        f"Routing strategy hint: {routing_strategy}\n"
        f"Available members:\n{roster}\n"
        f"\nUser request: {message}\n"
    )


async def plan_team_run(
    *,
    message: str,
    team_name: str,
    capabilities: list[str],
    custom_agents: list[dict[str, Any]],
    routing_strategy: str,
    model: str | None,
    temperature: float | None,
    user_balance: int,
    max_credits: int | None,
) -> TeamPlan:
    """One LLM call + deterministic validation. Returns a safe-to-execute plan.

    Raises PlanValidationError if the planner produces something invalid.
    """
    prompt = _format_planner_prompt(
        message=message,
        team_name=team_name,
        capabilities=capabilities,
        custom_agents=custom_agents,
        routing_strategy=routing_strategy,
    )

    if model is not None or temperature is not None:
        chat_model = make_fal_chat_model(model=model, temperature=temperature)
        result = await planner_agent.run(prompt, model=chat_model)
    else:
        result = await planner_agent.run(prompt)

    plan = result.output
    validate_plan(plan, user_balance=user_balance, max_credits=max_credits)
    return plan
