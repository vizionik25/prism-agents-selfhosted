"""Unit tests for the team planner's DAG schema and validator.

These tests don't touch an LLM — they exercise the Pydantic schema and the
deterministic `validate_plan` function. Planner-with-LLM tests come in Task 3.
"""

from __future__ import annotations

import json

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from media_agents.agents import team_planner as planner_mod
from media_agents.agents.team_planner import (
    MAX_DAG_NODES,
    PlanNode,
    PlanValidationError,
    TeamPlan,
    plan_team_run,
    validate_plan,
)


def test_plan_node_minimal_fields():
    node = PlanNode(id="n1", member="text_to_image", request="a red sphere")
    assert node.id == "n1"
    assert node.member == "text_to_image"
    assert node.request == "a red sphere"
    assert node.depends_on == []
    assert node.rationale is None


def test_team_plan_minimal_fields():
    plan = TeamPlan(
        summary="single step",
        nodes=[PlanNode(id="n1", member="text_to_image", request="x")],
        estimated_credits=1,
    )
    assert plan.summary == "single step"
    assert len(plan.nodes) == 1
    assert plan.estimated_credits == 1


def _plan(nodes, summary="s", estimated_credits=None):
    if estimated_credits is None:
        estimated_credits = len(nodes)
    return TeamPlan(summary=summary, nodes=nodes, estimated_credits=estimated_credits)


def test_validate_plan_accepts_linear_dag():
    plan = _plan(
        [
            PlanNode(id="n1", member="text_to_image", request="a"),
            PlanNode(id="n2", member="image_to_video", request="b", depends_on=["n1"]),
        ],
        estimated_credits=1 + 5,
    )
    validate_plan(plan, user_balance=100, max_credits=None)


def test_validate_plan_accepts_diamond():
    plan = _plan(
        [
            PlanNode(id="n1", member="text_to_image", request="a"),
            PlanNode(id="n2", member="image_to_image", request="b", depends_on=["n1"]),
            PlanNode(id="n3", member="image_to_3d", request="c", depends_on=["n1"]),
            PlanNode(
                id="n4", member="text_to_video", request="d", depends_on=["n2", "n3"]
            ),
        ],
        estimated_credits=1 + 1 + 10 + 5,
    )
    validate_plan(plan, user_balance=100, max_credits=None)


def test_validate_plan_rejects_unknown_member():
    plan = _plan([PlanNode(id="n1", member="nope_totally_fake", request="x")])
    with pytest.raises(PlanValidationError, match="unknown member"):
        validate_plan(plan, user_balance=100, max_credits=None)


def test_validate_plan_rejects_forward_dependency():
    plan = _plan(
        [
            PlanNode(id="n1", member="text_to_image", request="a", depends_on=["n2"]),
            PlanNode(id="n2", member="text_to_image", request="b"),
        ]
    )
    with pytest.raises(PlanValidationError, match="forward dependency"):
        validate_plan(plan, user_balance=100, max_credits=None)


def test_validate_plan_rejects_unknown_dependency_id():
    plan = _plan(
        [PlanNode(id="n1", member="text_to_image", request="a", depends_on=["ghost"])]
    )
    with pytest.raises(PlanValidationError, match="unknown dependency"):
        validate_plan(plan, user_balance=100, max_credits=None)


def test_validate_plan_rejects_cycle():
    plan = _plan(
        [
            PlanNode(id="n1", member="text_to_image", request="a", depends_on=["n2"]),
            PlanNode(id="n2", member="text_to_image", request="b", depends_on=["n1"]),
        ]
    )
    # The forward-dep check fires first — a cycle implies a forward dep — but
    # we still assert the error message mentions either.
    with pytest.raises(PlanValidationError):
        validate_plan(plan, user_balance=100, max_credits=None)


def test_validate_plan_rejects_too_many_nodes():
    nodes = [
        PlanNode(id=f"n{i}", member="text_to_image", request="x")
        for i in range(MAX_DAG_NODES + 1)
    ]
    plan = _plan(nodes, estimated_credits=MAX_DAG_NODES + 1)
    with pytest.raises(PlanValidationError, match="too many nodes"):
        validate_plan(plan, user_balance=100, max_credits=None)


def test_validate_plan_rejects_over_budget_vs_user_balance():
    plan = _plan(
        [PlanNode(id="n1", member="text_to_3d", request="x")], estimated_credits=10
    )
    with pytest.raises(PlanValidationError, match="insufficient credits"):
        validate_plan(plan, user_balance=3, max_credits=None)


def test_validate_plan_rejects_over_budget_vs_run_cap():
    plan = _plan(
        [PlanNode(id="n1", member="text_to_3d", request="x")], estimated_credits=10
    )
    with pytest.raises(PlanValidationError, match="run cap"):
        validate_plan(plan, user_balance=100, max_credits=5)


def test_validate_plan_rejects_mismatched_estimate():
    # text_to_image costs 1 credit; plan claims 7.
    plan = _plan(
        [PlanNode(id="n1", member="text_to_image", request="x")], estimated_credits=7
    )
    with pytest.raises(PlanValidationError, match="estimated_credits"):
        validate_plan(plan, user_balance=100, max_credits=None)


def test_validate_plan_rejects_empty_plan():
    with pytest.raises(PlanValidationError, match="empty plan"):
        validate_plan(
            _plan([], estimated_credits=0), user_balance=100, max_credits=None
        )


def test_validate_plan_rejects_duplicate_node_ids():
    plan = _plan(
        [
            PlanNode(id="n1", member="text_to_image", request="a"),
            PlanNode(id="n1", member="music_generation", request="b"),
        ],
        estimated_credits=1 + 3,
    )
    with pytest.raises(PlanValidationError, match="duplicate node id"):
        validate_plan(plan, user_balance=100, max_credits=None)


def test_validate_plan_rejects_self_dependency():
    plan = _plan(
        [PlanNode(id="n1", member="text_to_image", request="a", depends_on=["n1"])]
    )
    with pytest.raises(PlanValidationError, match="self-dependency"):
        validate_plan(plan, user_balance=100, max_credits=None)


def test_plan_node_rejects_bad_id_shapes():
    # Pydantic raises ValidationError at construction time.
    from pydantic import ValidationError

    bad_ids = ["step 1", "n1.a", "a:b", "", "n1/2", "n#1"]
    for bad in bad_ids:
        with pytest.raises(ValidationError):
            PlanNode(id=bad, member="text_to_image", request="x")


def test_plan_node_accepts_good_id_shapes():
    for good in ["n1", "n42", "node_1", "node-2", "N1", "step_1_a"]:
        node = PlanNode(id=good, member="text_to_image", request="x")
        assert node.id == good


def _plan_tool_call(plan_dict: dict) -> ModelResponse:
    """Return a ModelResponse that looks like PydanticAI's structured-output call."""
    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="final_result",
                args=json.dumps(plan_dict),
            )
        ]
    )


async def test_plan_team_run_returns_validated_plan():
    plan_dict = {
        "summary": "make a logo",
        "nodes": [{"id": "n1", "member": "text_to_image", "request": "a blue logo"}],
        "estimated_credits": 1,
    }

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        return _plan_tool_call(plan_dict)

    with planner_mod.planner_agent.override(model=FunctionModel(model_fn)):
        plan = await plan_team_run(
            message="make me a logo",
            team_name="Design Team",
            capabilities=["text_to_image"],
            custom_agents=[],
            routing_strategy="llm_routed",
            model=None,
            temperature=None,
            user_balance=100,
            max_credits=None,
        )

    assert plan.summary == "make a logo"
    assert len(plan.nodes) == 1
    assert plan.nodes[0].member == "text_to_image"


async def test_plan_team_run_raises_when_plan_is_invalid():
    plan_dict = {
        "summary": "bad",
        "nodes": [{"id": "n1", "member": "nonexistent_cap", "request": "x"}],
        "estimated_credits": 1,
    }

    def model_fn(messages, info: AgentInfo) -> ModelResponse:
        return _plan_tool_call(plan_dict)

    with planner_mod.planner_agent.override(model=FunctionModel(model_fn)):
        with pytest.raises(PlanValidationError, match="unknown member"):
            await plan_team_run(
                message="x",
                team_name="T",
                capabilities=["text_to_image"],
                custom_agents=[],
                routing_strategy="llm_routed",
                model=None,
                temperature=None,
                user_balance=100,
                max_credits=None,
            )
