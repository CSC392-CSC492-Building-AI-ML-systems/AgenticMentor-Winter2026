"""
Comprehensive end-to-end test for the full orchestrator (Branch 3).

Exercises all Branch 3 features in a realistic multi-turn flow:
  - Turn 1: requirements gathering (auto mode)
  - Turn 2: architecture design → downstream execution_planner planned
  - Turn 3: change request → re-runs architect + downstream
  - Turn 4: manual mode agent selection
  - Assertions: phase transitions, conversation history, agent_results,
    available_agents, state persistence across turns

No real LLM required — uses fake agents and mocked graph.

Run with:
    python tests/integration/test_orchestrator_full.py
or:
    python -m pytest tests/integration/test_orchestrator_full.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.orchestrator.agent_store import AGENT_STORE, get_agent_by_id
from src.orchestrator.execution_plan import ExecutionPlan
from src.orchestrator.master_agent import MasterOrchestrator, PHASE_TRANSITION_MAP
from src.state.project_state import ArchitectureDefinition, ProjectState, Requirements
from src.state.state_manager import StateManager
from src.storage.memory_store import InMemoryPersistenceAdapter


# ---------------------------------------------------------------------------
# Fake agents
# ---------------------------------------------------------------------------

class FakeRequirementsCollector:
    def __init__(self):
        self.call_count = 0

    async def process_message(self, user_input, requirements_state, history):
        self.call_count += 1
        return {
            "response": "I've captured your requirements.",
            "requirements": None,
        }


class FakeArchitectAgent:
    def __init__(self, tech_stack: dict | None = None):
        self.call_count = 0
        self._tech_stack = tech_stack or {"backend": "Python/FastAPI", "frontend": "React"}

    async def process(self, input_data: dict) -> dict:
        self.call_count += 1
        return {
            "state_delta": {
                "architecture": {
                    "tech_stack": self._tech_stack,
                    "tech_stack_rationale": "Fake rationale",
                    "data_schema": None,
                    "system_diagram": None,
                    "api_design": [],
                    "deployment_strategy": None,
                }
            },
            "summary": f"Architecture: {self._tech_stack}",
        }


class FakeExecutionPlannerAgent:
    def __init__(self):
        self.call_count = 0

    async def process(self, input_data: dict) -> dict:
        self.call_count += 1
        return {"state_delta": {}, "summary": "Execution plan ready."}


# ---------------------------------------------------------------------------
# Registry that tracks get_agent calls
# ---------------------------------------------------------------------------

class TrackingRegistry:
    def __init__(self, agents: dict):
        self._agents = agents
        self.call_log: list[str] = []  # ordered list of agent_ids fetched

    def get_agent(self, agent_id: str):
        agent = self._agents.get(agent_id)
        if agent is not None:
            self.call_log.append(agent_id)
        return agent


# ---------------------------------------------------------------------------
# Orchestrator factory
# ---------------------------------------------------------------------------

def _plan(*agent_ids: str) -> ExecutionPlan:
    plan = ExecutionPlan()
    for aid in agent_ids:
        entry = get_agent_by_id(aid)
        plan.add_task(agent_id=aid, required_context=(entry or {}).get("requires") or [])
    return plan


def _make_orch(state_manager, project_state, registry, plan, intent_label="auto"):
    orch = MasterOrchestrator.__new__(MasterOrchestrator)
    orch.state = state_manager
    orch.registry = registry
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={
        "project_state": project_state,
        "plan": plan,
        "intent": {"primary_intent": intent_label, "requires_agents": list(plan.tasks[0].agent_id if plan.tasks else []), "confidence": 0.9},
        "error": None,
    })
    orch._graph = mock_graph
    return orch


def _make_manual_orch(state_manager, registry):
    orch = MasterOrchestrator.__new__(MasterOrchestrator)
    orch.state = state_manager
    orch.registry = registry
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(side_effect=AssertionError("graph must not be called in manual mode"))
    orch._graph = mock_graph
    return orch


# ---------------------------------------------------------------------------
# Full multi-turn scenario
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_orchestration_multi_turn():
    """
    Simulates a realistic 4-turn project session:
      Turn 1: requirements gathering
      Turn 2: architecture design (downstream: execution_planner planned)
      Turn 3: change request (re-runs architect with new stack)
      Turn 4: manual mode (only requirements_collector)

    Verifies: phase transitions, conversation history growth,
    agent_results shape, available_agents, state persistence.
    """
    session_id = "test-full-e2e"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)

    # ── Seed initial state ──────────────────────────────────────────────────
    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    fake_req = FakeRequirementsCollector()
    fake_arch = FakeArchitectAgent(tech_stack={"backend": "Python/FastAPI"})
    fake_arch_v2 = FakeArchitectAgent(tech_stack={"backend": "Node.js/Express"})
    fake_exec = FakeExecutionPlannerAgent()

    # ── Turn 1: requirements gathering ──────────────────────────────────────
    print("\n  [Turn 1] Requirements gathering...")
    registry1 = TrackingRegistry({"requirements_collector": fake_req})
    state1 = await sm.load(session_id)
    orch1 = _make_orch(sm, state1, registry1, _plan("requirements_collector"), "requirements_gathering")
    r1 = await orch1.process_request("I want to build a task management app", session_id)

    assert "agent_results" in r1
    assert "available_agents" in r1
    assert len(r1["available_agents"]) == len(AGENT_STORE), "available_agents should list all store agents"
    assert any(ar["agent_id"] == "requirements_collector" for ar in r1["agent_results"])

    # Phase: requirements_collector → requirements_complete
    s1 = await persistence.get(session_id)
    assert s1["current_phase"] == "requirements_complete", f"Expected requirements_complete, got {s1['current_phase']}"
    assert len(s1["conversation_history"]) == 2  # user + assistant
    print(f"    phase={s1['current_phase']}, history={len(s1['conversation_history'])} entries ✓")

    # ── Turn 2: architecture design + downstream ─────────────────────────────
    print("  [Turn 2] Architecture design (+ downstream execution_planner)...")
    registry2 = TrackingRegistry({
        "project_architect": fake_arch,
        "execution_planner": fake_exec,
    })
    state2 = ProjectState(**await persistence.get(session_id))
    orch2 = _make_orch(sm, state2, registry2, _plan("project_architect", "execution_planner"), "architecture_design")
    r2 = await orch2.process_request("Design the architecture", session_id)

    # Both agents should appear in agent_results
    result_ids2 = [ar["agent_id"] for ar in r2["agent_results"]]
    assert "project_architect" in result_ids2
    assert "execution_planner" in result_ids2
    assert result_ids2.index("project_architect") < result_ids2.index("execution_planner")

    s2 = await persistence.get(session_id)
    # Phase: project_architect → architecture_complete (last transition wins)
    assert s2["current_phase"] == "architecture_complete", f"Expected architecture_complete, got {s2['current_phase']}"
    assert s2["architecture"]["tech_stack"]["backend"] == "Python/FastAPI"
    assert len(s2["conversation_history"]) == 4  # 2 more entries
    print(f"    phase={s2['current_phase']}, stack={s2['architecture']['tech_stack']}, history={len(s2['conversation_history'])} entries ✓")

    # ── Turn 3: change request (new tech stack) ──────────────────────────────
    print("  [Turn 3] Change request: switch to Node.js...")
    registry3 = TrackingRegistry({
        "project_architect": fake_arch_v2,
        "execution_planner": fake_exec,
    })
    state3 = ProjectState(**await persistence.get(session_id))
    orch3 = _make_orch(sm, state3, registry3, _plan("project_architect", "execution_planner"), "architecture_design")
    r3 = await orch3.process_request("Change backend to Node.js", session_id)

    s3 = await persistence.get(session_id)
    assert s3["architecture"]["tech_stack"]["backend"] == "Node.js/Express", \
        f"Expected Node.js/Express, got {s3['architecture']['tech_stack']}"
    assert len(s3["conversation_history"]) == 6  # 2 more entries
    print(f"    stack updated to {s3['architecture']['tech_stack']}, history={len(s3['conversation_history'])} entries ✓")

    # ── Turn 4: manual mode ──────────────────────────────────────────────────
    print("  [Turn 4] Manual mode: run requirements_collector only...")
    registry4 = TrackingRegistry({"requirements_collector": fake_req})
    orch4 = _make_manual_orch(sm, registry4)
    r4 = await orch4.process_request(
        "Re-collect requirements",
        session_id,
        agent_selection_mode="manual",
        selected_agent_id="requirements_collector",
    )

    assert r4["intent"]["primary_intent"] == "manual"
    assert "project_architect" not in registry4.call_log, "architect should not run in manual mode"
    s4 = await persistence.get(session_id)
    assert s4["agent_selection_mode"] == "manual"
    assert s4["selected_agent_id"] == "requirements_collector"
    assert len(s4["conversation_history"]) == 8  # 2 more entries
    print(f"    manual mode confirmed, history={len(s4['conversation_history'])} entries ✓")

    print("\n  PASS: full 4-turn orchestration scenario")


# ---------------------------------------------------------------------------
# Individual feature assertions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_available_agents_always_returns_full_store():
    """available_agents in response always contains all AGENT_STORE entries."""
    session_id = "test-full-avail"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)
    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    registry = TrackingRegistry({"requirements_collector": FakeRequirementsCollector()})
    orch = _make_orch(sm, seed, registry, _plan("requirements_collector"))
    r = await orch.process_request("Hello", session_id)

    store_ids = {e["id"] for e in AGENT_STORE}
    response_ids = {a["agent_id"] for a in r["available_agents"]}
    assert store_ids == response_ids
    for a in r["available_agents"]:
        assert "agent_id" in a
        assert "agent_name" in a
        assert "description" in a
        assert "phase_compatibility" in a
    print(f"  PASS: available_agents has all {len(store_ids)} agents with correct shape")


@pytest.mark.asyncio
async def test_phase_transition_map_covers_all_producing_agents():
    """PHASE_TRANSITION_MAP has an entry for every agent that produces artifacts."""
    for entry in AGENT_STORE:
        if entry.get("produces"):  # only agents that produce artifacts need a transition
            assert entry["id"] in PHASE_TRANSITION_MAP, \
                f"Agent '{entry['id']}' produces artifacts but has no entry in PHASE_TRANSITION_MAP"
    print(f"  PASS: PHASE_TRANSITION_MAP covers all {len(PHASE_TRANSITION_MAP)} producing agents")


@pytest.mark.asyncio
async def test_conversation_history_roles_always_alternate():
    """conversation_history always alternates user/assistant roles."""
    session_id = "test-full-roles"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)
    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    fake_req = FakeRequirementsCollector()
    for i in range(3):
        state = ProjectState(**await persistence.get(session_id))
        registry = TrackingRegistry({"requirements_collector": fake_req})
        orch = _make_orch(sm, state, registry, _plan("requirements_collector"))
        await orch.process_request(f"Message {i+1}", session_id)

    s = await persistence.get(session_id)
    history = s["conversation_history"]
    assert len(history) == 6  # 3 turns × 2 entries
    for i, entry in enumerate(history):
        expected_role = "user" if i % 2 == 0 else "assistant"
        assert entry["role"] == expected_role, \
            f"Entry {i}: expected role '{expected_role}', got '{entry['role']}'"
    print(f"  PASS: conversation history alternates correctly over 3 turns ({len(history)} entries)")


@pytest.mark.asyncio
async def test_agent_results_skipped_for_unimplemented_agents():
    """Unimplemented agents (registry returns None) appear as 'skipped' in agent_results."""
    session_id = "test-full-skip"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)
    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    # Registry returns None for execution_planner (not yet implemented)
    registry = TrackingRegistry({"project_architect": FakeArchitectAgent()})
    orch = _make_orch(sm, seed, registry, _plan("project_architect", "execution_planner"))
    r = await orch.process_request("Design and plan", session_id)

    skipped = [ar for ar in r["agent_results"] if ar["status"] == "skipped"]
    assert any(ar["agent_id"] == "execution_planner" for ar in skipped), \
        "execution_planner should be 'skipped' when registry returns None"
    print(f"  PASS: unimplemented agents appear as 'skipped' in agent_results")


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tests = [
        test_full_orchestration_multi_turn,
        test_available_agents_always_returns_full_store,
        test_phase_transition_map_covers_all_producing_agents,
        test_conversation_history_roles_always_alternate,
        test_agent_results_skipped_for_unimplemented_agents,
    ]

    async def run_all():
        print("\n=== Full Orchestration Test Suite (Branch 3) ===")
        passed = 0
        for test in tests:
            print(f"\nRunning {test.__name__}...")
            try:
                await test()
                passed += 1
            except AssertionError as e:
                print(f"  FAIL: {e}")
            except Exception as e:
                import traceback
                print(f"  ERROR: {type(e).__name__}: {e}")
                traceback.print_exc()
        print(f"\n{'='*50}")
        print(f"Results: {passed}/{len(tests)} passed")
        if passed < len(tests):
            sys.exit(1)

    asyncio.run(run_all())
