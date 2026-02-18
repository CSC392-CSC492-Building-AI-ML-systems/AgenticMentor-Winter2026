"""Unit tests for ExecutionPlanner.plan() (orchestrator)."""
import pytest

from src.orchestrator.execution_plan import ExecutionPlan, Task
from src.orchestrator.execution_planner import ExecutionPlanner
from src.state.project_state import (
    ProjectState,
    Requirements,
    ArchitectureDefinition,
)


def _state(
    session_id: str = "s1",
    current_phase: str = "initialization",
    requirements=None,
    architecture=None,
):
    return ProjectState(
        session_id=session_id,
        current_phase=current_phase,
        requirements=requirements or Requirements(),
        architecture=architecture or ArchitectureDefinition(),
    )


@pytest.fixture
def planner():
    return ExecutionPlanner()


def test_architecture_design_empty_requirements_prepends_collector(planner):
    """Intent architecture_design, empty requirements -> plan has requirements_collector then project_architect."""
    intent = {
        "primary_intent": "architecture_design",
        "requires_agents": ["project_architect"],
        "confidence": 0.9,
    }
    state = _state(current_phase="requirements_complete", requirements=Requirements())
    plan = planner.plan(intent, state)
    agent_ids = [t.agent_id for t in plan.tasks]
    assert "requirements_collector" in agent_ids
    assert "project_architect" in agent_ids
    assert agent_ids.index("requirements_collector") < agent_ids.index(
        "project_architect"
    )


def test_architecture_design_with_requirements_architect_only(planner):
    """Intent architecture_design, state with requirements -> plan can be just project_architect."""
    intent = {
        "primary_intent": "architecture_design",
        "requires_agents": ["project_architect"],
        "confidence": 0.9,
    }
    state = _state(
        current_phase="requirements_complete",
        requirements=Requirements(functional=["Login"], constraints=["Python"]),
    )
    plan = planner.plan(intent, state)
    agent_ids = [t.agent_id for t in plan.tasks]
    assert "project_architect" in agent_ids
    assert len(plan.tasks) >= 1


def test_export_exporter_only(planner):
    """Intent export, state with content -> plan includes exporter."""
    intent = {"primary_intent": "export", "requires_agents": ["exporter"], "confidence": 0.9}
    state = _state(
        current_phase="architecture_complete",
        requirements=Requirements(functional=["API"]),
        architecture=ArchitectureDefinition(tech_stack={"backend": "Python"}),
    )
    plan = planner.plan(intent, state)
    agent_ids = [t.agent_id for t in plan.tasks]
    assert "exporter" in agent_ids
    for t in plan.tasks:
        if t.agent_id == "exporter":
            assert "*" in t.required_context or len(t.required_context) >= 1
            break


def test_unknown_intent_full_pipeline_default(planner):
    """Intent unknown or empty requires_agents -> default to full pipeline; phase filters which agents run."""
    intent = {"primary_intent": "unknown", "requires_agents": [], "confidence": 0.0}
    state = _state(current_phase="architecture_complete")
    plan = planner.plan(intent, state)
    agent_ids = [t.agent_id for t in plan.tasks]
    assert len(plan.tasks) >= 4
    assert "requirements_collector" in agent_ids
    assert "project_architect" in agent_ids
    assert "execution_planner" in agent_ids
    assert "exporter" in agent_ids
    assert agent_ids.index("requirements_collector") < agent_ids.index("project_architect")
    assert agent_ids.index("project_architect") < agent_ids.index("execution_planner")
    assert agent_ids.index("execution_planner") < agent_ids.index("exporter")


def test_requirements_gathering_one_task(planner):
    """Requirements gathering intent -> plan has requirements_collector."""
    intent = {
        "primary_intent": "requirements_gathering",
        "requires_agents": ["requirements_collector"],
        "confidence": 0.8,
    }
    state = _state(current_phase="initialization")
    plan = planner.plan(intent, state)
    assert len(plan.tasks) >= 1
    assert plan.tasks[0].agent_id == "requirements_collector"


def test_plan_task_has_required_context(planner):
    """Each task has required_context from AGENT_STORE."""
    intent = {"primary_intent": "export", "requires_agents": ["exporter"], "confidence": 0.9}
    state = _state(
        current_phase="architecture_complete",
        requirements=Requirements(functional=["x"]),
    )
    plan = planner.plan(intent, state)
    for t in plan.tasks:
        assert isinstance(t, Task)
        assert t.agent_id
        assert isinstance(t.required_context, list)
