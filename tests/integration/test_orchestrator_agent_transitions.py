"""
Agent transition test suite: every intent → correct agents in plan, phase compatibility, and multi-step flows.
No API calls except the optional E2E test (skipped when GEMINI_API_KEY/GOOGLE_API_KEY not set).

How to run:
  - All orchestrator tests (unit + integration):
      pytest tests/unit/test_orchestrator_graph.py tests/unit/test_intent_classifier.py tests/unit/test_execution_planner.py tests/integration/test_orchestrator_agent_transitions.py tests/integration/test_orchestrator_e2e.py -v
  - Only this transition suite:
      pytest tests/integration/test_orchestrator_agent_transitions.py -v
  - E2E with real LLM (set GEMINI_API_KEY):
      pytest tests/integration/test_orchestrator_agent_transitions.py tests/integration/test_orchestrator_e2e.py -v
  - From project root; conftest.py adds project root to path.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.state.project_state import (
    ProjectState,
    Requirements,
    ArchitectureDefinition,
)
from src.orchestrator.graph import build_orchestrator_graph
from src.orchestrator.intent_classifier import IntentClassifier
from src.orchestrator.execution_planner import ExecutionPlanner


# ----- Fixtures: state managers that return seeded state for each phase -----


def _make_mock_sm(initial_state: ProjectState):
    """State manager that always returns the same seeded state for any session."""
    class MockSM:
        async def load(self, session_id: str):
            return initial_state
    return MockSM()  # return instance


@pytest.fixture
def graph_components():
    """Intent classifier and execution planner (no LLM)."""
    return IntentClassifier(llm=None), ExecutionPlanner()


# ----- 1. Intent → plan: each intent produces the correct agent(s) in plan -----


@pytest.mark.asyncio
async def test_intent_requirements_gathering_plan_has_requirements_collector(graph_components):
    """Phase initialization + 'clarify goals' → intent requirements_gathering, plan has requirements_collector."""
    ic, ep = graph_components
    state = ProjectState(
        session_id="t1",
        current_phase="initialization",
        requirements=Requirements(),
    )
    graph = build_orchestrator_graph(_make_mock_sm(state), ic, ep)
    result = await graph.ainvoke({
        "user_input": "I want to clarify our goals",
        "session_id": "t1",
    })
    assert result.get("error") is None
    assert result["intent"]["primary_intent"] == "requirements_gathering"
    agent_ids = [t.agent_id for t in result["plan"].tasks]
    assert "requirements_collector" in agent_ids


@pytest.mark.asyncio
async def test_intent_architecture_design_plan_has_project_architect(graph_components):
    """Phase requirements_complete + 'generate architecture' → intent architecture_design, plan has project_architect."""
    ic, ep = graph_components
    state = ProjectState(
        session_id="t2",
        current_phase="requirements_complete",
        requirements=Requirements(functional=["Auth", "Dashboard"]),
    )
    graph = build_orchestrator_graph(_make_mock_sm(state), ic, ep)
    result = await graph.ainvoke({
        "user_input": "generate the architecture and tech stack",
        "session_id": "t2",
    })
    assert result.get("error") is None
    assert result["intent"]["primary_intent"] == "architecture_design"
    agent_ids = [t.agent_id for t in result["plan"].tasks]
    assert "project_architect" in agent_ids


@pytest.mark.asyncio
async def test_intent_execution_planning_plan_has_execution_planner(graph_components):
    """Phase architecture_complete + 'roadmap' → intent execution_planning, plan has execution_planner."""
    ic, ep = graph_components
    state = ProjectState(
        session_id="t3",
        current_phase="architecture_complete",
        requirements=Requirements(functional=["API"]),
        architecture=ArchitectureDefinition(tech_stack={"frontend": "React", "backend": "FastAPI"}),
    )
    graph = build_orchestrator_graph(_make_mock_sm(state), ic, ep)
    result = await graph.ainvoke({
        "user_input": "give me a roadmap and milestones",
        "session_id": "t3",
    })
    assert result.get("error") is None
    assert result["intent"]["primary_intent"] == "execution_planning"
    agent_ids = [t.agent_id for t in result["plan"].tasks]
    assert "execution_planner" in agent_ids


@pytest.mark.asyncio
async def test_intent_mockup_creation_plan_has_mockup_agent(graph_components):
    """Phase architecture_complete + 'wireframe' → intent mockup_creation, plan has mockup_agent."""
    ic, ep = graph_components
    state = ProjectState(
        session_id="t4",
        current_phase="architecture_complete",
        requirements=Requirements(functional=["Login screen"]),
        architecture=ArchitectureDefinition(tech_stack={"frontend": "React"}),
    )
    graph = build_orchestrator_graph(_make_mock_sm(state), ic, ep)
    result = await graph.ainvoke({
        "user_input": "I need UI wireframes and user flow",
        "session_id": "t4",
    })
    assert result.get("error") is None
    assert result["intent"]["primary_intent"] == "mockup_creation"
    agent_ids = [t.agent_id for t in result["plan"].tasks]
    assert "mockup_agent" in agent_ids


@pytest.mark.asyncio
async def test_intent_export_plan_has_exporter(graph_components):
    """Any phase + 'export to PDF' → intent export, plan has exporter."""
    ic, ep = graph_components
    state = ProjectState(
        session_id="t5",
        current_phase="initialization",
        requirements=Requirements(),
    )
    graph = build_orchestrator_graph(_make_mock_sm(state), ic, ep)
    result = await graph.ainvoke({
        "user_input": "export the document to PDF",
        "session_id": "t5",
    })
    assert result.get("error") is None
    assert result["intent"]["primary_intent"] == "export"
    agent_ids = [t.agent_id for t in result["plan"].tasks]
    assert "exporter" in agent_ids


@pytest.mark.asyncio
async def test_intent_unknown_plan_falls_back_to_requirements_collector(graph_components):
    """Gibberish input → intent unknown, plan falls back to requirements_collector only."""
    ic, ep = graph_components
    state = ProjectState(
        session_id="t6",
        current_phase="architecture_complete",
        requirements=Requirements(functional=["Auth"]),
        architecture=ArchitectureDefinition(tech_stack={"frontend": "React"}),
    )
    graph = build_orchestrator_graph(_make_mock_sm(state), ic, ep)
    result = await graph.ainvoke({
        "user_input": "xyzzz qqq nothing matches",
        "session_id": "t6",
    })
    assert result.get("error") is None
    assert result["intent"]["primary_intent"] == "unknown"
    agent_ids = [t.agent_id for t in result["plan"].tasks]
    assert agent_ids == ["requirements_collector"]


# ----- 2. Phase compatibility: architect only when phase allows -----


@pytest.mark.asyncio
async def test_architecture_intent_blocked_in_initialization_phase(graph_components):
    """In initialization, an architecture request should not run project_architect before requirements are gathered."""
    ic, ep = graph_components
    state = ProjectState(
        session_id="t7",
        current_phase="initialization",
        requirements=Requirements(functional=["Something"]),
    )
    graph = build_orchestrator_graph(_make_mock_sm(state), ic, ep)
    result = await graph.ainvoke({
        "user_input": "generate the architecture",
        "session_id": "t7",
    })
    plan_agent_ids = [t.agent_id for t in result["plan"].tasks]
    assert result["intent"]["primary_intent"] in ("architecture_design", "unknown", "requirements_gathering")
    assert "project_architect" not in plan_agent_ids, "project_architect must be excluded in initialization phase"
    assert isinstance(plan_agent_ids, list)


@pytest.mark.asyncio
async def test_export_available_in_any_phase(graph_components):
    """Export intent works in any phase (phase_compatibility *)."""
    for phase in ("initialization", "requirements_complete", "architecture_complete", "planning_complete"):
        ic, ep = graph_components
        state = ProjectState(session_id="t8", current_phase=phase, requirements=Requirements())
        graph = build_orchestrator_graph(_make_mock_sm(state), ic, ep)
        result = await graph.ainvoke({
            "user_input": "download as PDF",
            "session_id": "t8",
        })
        assert result.get("error") is None
        assert result["intent"]["primary_intent"] == "export"
        agent_ids = [t.agent_id for t in result["plan"].tasks]
        assert "exporter" in agent_ids


# ----- 3. Multi-step transition: two turns, plan updates correctly -----


@pytest.mark.asyncio
async def test_transition_requirements_then_architecture_plan(graph_components):
    """Turn 1: initialization + 'clarify goals' → plan has requirements_collector. Turn 2: requirements_complete + 'generate architecture' → plan has project_architect."""
    ic, ep = graph_components

    state1 = ProjectState(
        session_id="multi",
        current_phase="initialization",
        requirements=Requirements(),
    )
    graph = build_orchestrator_graph(_make_mock_sm(state1), ic, ep)
    r1 = await graph.ainvoke({"user_input": "I want to clarify our goals", "session_id": "multi"})
    assert r1["intent"]["primary_intent"] == "requirements_gathering"
    assert "requirements_collector" in [t.agent_id for t in r1["plan"].tasks]

    state2 = ProjectState(
        session_id="multi",
        current_phase="requirements_complete",
        requirements=Requirements(functional=["Auth"], constraints=["Python"]),
    )
    graph2 = build_orchestrator_graph(_make_mock_sm(state2), ic, ep)
    r2 = await graph2.ainvoke({"user_input": "generate the architecture", "session_id": "multi"})
    assert r2["intent"]["primary_intent"] == "architecture_design"
    assert "project_architect" in [t.agent_id for t in r2["plan"].tasks]


@pytest.mark.asyncio
async def test_transition_architecture_then_roadmap_plan(graph_components):
    """requirements_complete + 'architecture' → architect in plan. architecture_complete + 'roadmap' → execution_planner in plan."""
    ic, ep = graph_components

    state1 = ProjectState(
        session_id="ar",
        current_phase="requirements_complete",
        requirements=Requirements(functional=["API"]),
    )
    graph = build_orchestrator_graph(_make_mock_sm(state1), ic, ep)
    r1 = await graph.ainvoke({"user_input": "generate the architecture", "session_id": "ar"})
    assert "project_architect" in [t.agent_id for t in r1["plan"].tasks]

    state2 = ProjectState(
        session_id="ar",
        current_phase="architecture_complete",
        requirements=Requirements(functional=["API"]),
        architecture=ArchitectureDefinition(tech_stack={"backend": "FastAPI"}),
    )
    graph2 = build_orchestrator_graph(_make_mock_sm(state2), ic, ep)
    r2 = await graph2.ainvoke({"user_input": "give me a roadmap and timeline", "session_id": "ar"})
    assert r2["intent"]["primary_intent"] == "execution_planning"
    assert "execution_planner" in [t.agent_id for t in r2["plan"].tasks]


# ----- 4. E2E with real orchestrator (optional, needs API key) -----


SKIP_REAL_LLM = not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY")


@pytest.mark.asyncio
@pytest.mark.skipif(SKIP_REAL_LLM, reason="GEMINI_API_KEY or GOOGLE_API_KEY not set")
@pytest.mark.slow  # Real architect + exporter; skip with: pytest -m "not slow"
async def test_e2e_orchestrator_transition_architecture_then_export():
    """E2E: seed requirements_complete, run 'generate architecture', then 'export to PDF'. State and response shape ok."""
    from src.state.state_manager import StateManager
    from src.storage.memory_store import InMemoryPersistenceAdapter
    from src.orchestrator.master_agent import MasterOrchestrator

    session_id = "e2e-transition-1"
    persistence = InMemoryPersistenceAdapter()
    state_manager = StateManager(persistence)
    seed = ProjectState(
        session_id=session_id,
        current_phase="requirements_complete",
        requirements=Requirements(
            functional=["User auth", "Dashboard"],
            constraints=["Python backend"],
        ),
    )
    await persistence.save(session_id, seed.model_dump())

    orch = MasterOrchestrator(state_manager, use_llm=True)

    r1 = await orch.process_request("generate the architecture", session_id)
    assert "message" in r1 and "state_snapshot" in r1
    if not (r1.get("message") or "").startswith("Error:"):
        assert "project_state" in r1

    r2 = await orch.process_request("export the document to PDF", session_id)
    assert "message" in r2 and "state_snapshot" in r2
    assert "intent" in r2
    assert r2["intent"]["primary_intent"] == "export"
    assert "exporter" in [t.agent_id for t in r2["plan"].tasks]
