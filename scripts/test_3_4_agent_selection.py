"""
Standalone test for Part 3.4 — Auto/Manual Agent Selection Mode.
Runs with plain `python scripts/test_3_4_agent_selection.py`.
Patches _graph.ainvoke to skip LangGraph/LangChain entirely.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.state.project_state import ProjectState, Requirements
from src.state.state_manager import StateManager
from src.storage.memory_store import InMemoryPersistenceAdapter
from src.orchestrator.execution_plan import ExecutionPlan, Task
from src.orchestrator.master_agent import MasterOrchestrator


# ---------------------------------------------------------------------------
# Fake agents
# ---------------------------------------------------------------------------
class FakeRequirementsCollector:
    async def process_message(self, user_input, requirements_state, history):
        return {"response": "Requirements noted.", "requirements": None}


class FakeRegistry:
    def get_agent(self, agent_id):
        if agent_id == "requirements_collector":
            return FakeRequirementsCollector()
        return None


def _make_orchestrator_auto(state_manager, project_state):
    """Auto mode: _graph.ainvoke returns a plan with requirements_collector."""
    orch = MasterOrchestrator.__new__(MasterOrchestrator)
    orch.state = state_manager
    orch.registry = FakeRegistry()

    plan = ExecutionPlan()
    plan.add_task(agent_id="requirements_collector", required_context=[])

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={
        "project_state": project_state,
        "plan": plan,
        "intent": {"primary_intent": "requirements_gathering", "requires_agents": ["requirements_collector"], "confidence": 0.9},
        "error": None,
    })
    orch._graph = mock_graph
    return orch


def _make_orchestrator_manual(state_manager):
    """Manual mode: _graph should never be called."""
    orch = MasterOrchestrator.__new__(MasterOrchestrator)
    orch.state = state_manager
    orch.registry = FakeRegistry()

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(side_effect=AssertionError("_graph.ainvoke should NOT be called in manual mode"))
    orch._graph = mock_graph
    return orch


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
async def test_auto_mode_response_has_agent_results_and_available_agents():
    session_id = "test-34-auto"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)

    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    orch = _make_orchestrator_auto(sm, seed)
    response = await orch.process_request("Build me an app", session_id)

    assert "agent_results" in response, "Response missing agent_results"
    assert "available_agents" in response, "Response missing available_agents"
    assert isinstance(response["agent_results"], list)
    assert isinstance(response["available_agents"], list)
    assert len(response["available_agents"]) > 0, "available_agents should not be empty"
    print(f"  PASS: auto mode response has agent_results ({len(response['agent_results'])}) and available_agents ({len(response['available_agents'])})")


async def test_auto_mode_agent_results_shape():
    session_id = "test-34-auto-shape"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)

    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    orch = _make_orchestrator_auto(sm, seed)
    response = await orch.process_request("Build me an app", session_id)

    for ar in response["agent_results"]:
        assert "agent_id" in ar
        assert "status" in ar
        assert ar["status"] in ("success", "skipped", "error")
    print(f"  PASS: all agent_results entries have correct shape")


async def test_manual_mode_bypasses_graph():
    """Manual mode should not call _graph.ainvoke."""
    session_id = "test-34-manual"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)

    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    orch = _make_orchestrator_manual(sm)
    # Should NOT raise — graph.ainvoke is patched to raise if called
    response = await orch.process_request(
        "Run requirements",
        session_id,
        agent_selection_mode="manual",
        selected_agent_id="requirements_collector",
    )
    assert response["intent"]["primary_intent"] == "manual"
    print(f"  PASS: manual mode bypassed _graph.ainvoke, intent=manual")


async def test_manual_mode_persists_selection():
    session_id = "test-34-manual-persist"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)

    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    orch = _make_orchestrator_manual(sm)
    await orch.process_request(
        "Run requirements",
        session_id,
        agent_selection_mode="manual",
        selected_agent_id="requirements_collector",
    )

    state_dict = await persistence.get(session_id)
    assert state_dict.get("agent_selection_mode") == "manual"
    assert state_dict.get("selected_agent_id") == "requirements_collector"
    print(f"  PASS: manual mode selection persisted to state")


async def test_available_agents_contains_all_store_agents():
    session_id = "test-34-avail"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)

    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    orch = _make_orchestrator_auto(sm, seed)
    response = await orch.process_request("Hello", session_id)

    from src.orchestrator.agent_store import AGENT_STORE
    store_ids = {e["id"] for e in AGENT_STORE}
    response_ids = {a["agent_id"] for a in response["available_agents"]}
    assert store_ids == response_ids, f"Mismatch: store={store_ids}, response={response_ids}"
    print(f"  PASS: available_agents contains all {len(store_ids)} agents from AGENT_STORE")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
async def main():
    print("\n=== Part 3.4 — Auto/Manual Agent Selection Mode Tests ===\n")
    tests = [
        test_auto_mode_response_has_agent_results_and_available_agents,
        test_auto_mode_agent_results_shape,
        test_manual_mode_bypasses_graph,
        test_manual_mode_persists_selection,
        test_available_agents_contains_all_store_agents,
    ]
    passed = 0
    for test in tests:
        print(f"Running {test.__name__}...")
        try:
            await test()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {e}")
        except Exception as e:
            import traceback
            print(f"  ERROR: {type(e).__name__}: {e}")
            traceback.print_exc()

    print(f"\n{'='*55}")
    print(f"Results: {passed}/{len(tests)} passed")
    if passed < len(tests):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
