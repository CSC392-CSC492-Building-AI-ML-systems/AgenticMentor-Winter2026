"""
Comprehensive end-to-end test for the full orchestrator (Branch 3).

Exercises Branch 3 features in a realistic multi-turn flow:
  - Turn 1: requirements gathering (auto mode)
  - Turn 2: architecture design checkpoint
  - Turn 3: explicit continue to execution planner
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
from src.protocols.schemas import RequirementsState


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
            "requirements": RequirementsState(
                project_type="web app",
                target_users=["solo user"],
                key_features=["Task creation", "Task list"],
                technical_constraints=["Next.js"],
                business_goals=["Stay organized"],
                timeline="2 weeks",
                budget="$0",
                is_complete=True,
                progress=1.0,
            ),
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


class FakeMockupAgent:
    async def process(self, input_data: dict) -> dict:
        return {
            "state_delta": {
                "mockups": [
                    {
                        "screen_name": "Dashboard",
                        "screen_id": "dashboard",
                        "wireframe_code": '{"version": 1}',
                        "user_flow": "Open dashboard",
                        "interactions": [],
                        "template_used": "default",
                    }
                ]
            },
            "summary": "Mockup ready.",
        }


class FakeExporterAgent:
    async def execute(self, input, context=None, tools=None):
        class Out:
            content = "Export complete."
            state_delta = {
                "export_artifacts": {
                    "executive_summary": "Summary",
                    "markdown_content": "# Export",
                    "saved_path": "outputs/full-test-export.pdf",
                    "generated_formats": ["markdown", "pdf"],
                    "exported_at": "2026-03-06T20:30:00",
                    "history": [
                        {
                            "saved_path": "outputs/full-test-export.pdf",
                            "generated_formats": ["markdown", "pdf"],
                            "exported_at": "2026-03-06T20:30:00",
                        }
                    ],
                }
            }

        return Out()


class ExplodingArchitectAgent:
    async def process(self, input_data: dict) -> dict:
        raise RuntimeError("architect crashed")


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
      Turn 2: architecture design checkpoint
      Turn 3: explicit continue to execution planner
      Turn 4: manual mode (only requirements_collector)

    Verifies: phase transitions, conversation history growth,
    agent_results shape, checkpoint metadata, available_agents, state persistence.
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
    assert len(r1["available_agents"]) == len(AGENT_STORE), "available_agents should still expose the full store with readiness metadata"
    req_agent = next(a for a in r1["available_agents"] if a["agent_id"] == "requirements_collector")
    arch_agent = next(a for a in r1["available_agents"] if a["agent_id"] == "project_architect")
    assert req_agent["is_available"] is True
    assert arch_agent["is_available"] is True
    assert any(ar["agent_id"] == "requirements_collector" for ar in r1["agent_results"])

    # Phase: requirements_collector → requirements_complete
    s1 = await persistence.get(session_id)
    assert s1["current_phase"] == "requirements_complete", f"Expected requirements_complete, got {s1['current_phase']}"
    assert s1["requirements"]["project_type"] == "web app"
    assert s1["requirements"]["target_users"] == ["solo user"]
    assert s1["requirements"]["business_goals"] == ["Stay organized"]
    assert s1["requirements"]["timeline"] == "2 weeks"
    assert s1["requirements"]["budget"] == "$0"
    assert s1["requirements"]["is_complete"] is True
    assert s1["requirements"]["progress"] == pytest.approx(1.0)
    assert len(s1["conversation_history"]) == 2  # user + assistant
    print(f"    phase={s1['current_phase']}, history={len(s1['conversation_history'])} entries ✓")

    # ── Turn 2: architecture design checkpoint ───────────────────────────────
    print("  [Turn 2] Architecture design checkpoint...")
    registry2 = TrackingRegistry({
        "project_architect": fake_arch,
        "execution_planner": fake_exec,
    })
    state2 = ProjectState(**await persistence.get(session_id))
    orch2 = _make_orch(sm, state2, registry2, _plan("project_architect", "execution_planner"), "architecture_design")
    r2 = await orch2.process_request("Design the architecture", session_id)

    result_ids2 = [ar["agent_id"] for ar in r2["agent_results"]]
    assert result_ids2 == ["project_architect"]
    assert r2["current_step"]["agent_id"] == "project_architect"
    assert r2["next_step"]["agent_id"] == "execution_planner"
    assert r2["awaiting_user_action"] is True

    s2 = await persistence.get(session_id)
    assert s2["current_phase"] == "architecture_complete", f"Expected architecture_complete, got {s2['current_phase']}"
    assert s2["awaiting_user_action"] is True
    assert s2["next_recommended_agent_id"] == "execution_planner"
    assert s2["architecture"]["tech_stack"]["backend"] == "Python/FastAPI"
    assert len(s2["conversation_history"]) == 4  # 2 more entries
    print(f"    phase={s2['current_phase']}, stack={s2['architecture']['tech_stack']}, history={len(s2['conversation_history'])} entries ✓")

    # ── Turn 3: explicit continue to execution planner ───────────────────────
    print("  [Turn 3] Continue to execution planner...")
    registry3 = TrackingRegistry({
        "execution_planner": fake_exec,
    })
    state3 = ProjectState(**await persistence.get(session_id))
    orch3 = _make_orch(sm, state3, registry3, _plan("project_architect", "execution_planner"), "architecture_design")
    r3 = await orch3.process_request("continue", session_id)

    s3 = await persistence.get(session_id)
    assert r3["current_step"]["agent_id"] == "execution_planner"
    assert r3["awaiting_user_action"] is False
    assert s3["current_phase"] == "planning_complete"
    assert s3["last_completed_agent_id"] == "execution_planner"
    assert len(s3["conversation_history"]) == 6  # 2 more entries
    print(f"    phase advanced to {s3['current_phase']}, history={len(s3['conversation_history'])} entries ✓")

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
async def test_available_agents_include_readiness_metadata():
    """available_agents should expose all agents plus readiness details for the current state."""
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
    availability = {a["agent_id"]: a for a in r["available_agents"]}
    for a in r["available_agents"]:
        assert "agent_id" in a
        assert "agent_name" in a
        assert "description" in a
        assert "phase_compatibility" in a
        assert "is_available" in a
        assert "blocked_by" in a
        assert "unmet_requires" in a
        assert "is_phase_compatible" in a
    assert availability["requirements_collector"]["is_available"] is True
    assert availability["project_architect"]["is_available"] is True
    print(f"  PASS: available_agents exposes readiness metadata for all {len(store_ids)} agents")


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
    """When the first auto-mode task is unavailable, it appears as skipped_unavailable in agent_results."""
    session_id = "test-full-skip"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)
    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    registry = TrackingRegistry({})
    orch = _make_orch(sm, seed, registry, _plan("project_architect", "execution_planner"))
    r = await orch.process_request("Design and plan", session_id)

    skipped = [ar for ar in r["agent_results"] if ar["status"] == "skipped_unavailable"]
    assert any(ar["agent_id"] == "project_architect" for ar in skipped), \
        "project_architect should be 'skipped_unavailable' when the first task is unavailable"
    print("  PASS: unavailable first task appears as skipped_unavailable")


@pytest.mark.asyncio
async def test_export_artifacts_persist_when_exporter_runs():
    """Exporter state_delta should persist saved path, formats, and history in canonical state."""
    session_id = "test-full-export"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)
    seed = ProjectState(
        session_id=session_id,
        current_phase="planning_complete",
        requirements=Requirements(),
        architecture=ArchitectureDefinition(tech_stack={"frontend": "React"}),
    )
    await persistence.save(session_id, seed.model_dump())

    registry = TrackingRegistry(
        {
            "exporter": FakeExporterAgent(),
        }
    )
    orch = _make_orch(sm, seed, registry, _plan("exporter"), "export")
    response = await orch.process_request("Export to PDF", session_id)

    persisted = await persistence.get(session_id)
    assert response["state_snapshot"]["export_artifacts"]["saved_path"] == "outputs/full-test-export.pdf"
    assert persisted["export_artifacts"]["generated_formats"] == ["markdown", "pdf"]
    assert persisted["export_artifacts"]["history"][0]["saved_path"] == "outputs/full-test-export.pdf"
    print("  PASS: export artifacts persist with saved_path, formats, and history")


@pytest.mark.asyncio
async def test_failure_message_surfaces_issue_summary():
    """User-facing response should surface structured failure summaries when the executed auto task fails."""
    session_id = "test-full-issues"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)
    seed = ProjectState(
        session_id=session_id,
        current_phase="requirements_complete",
        requirements=Requirements(functional=["Auth"]),
    )
    await persistence.save(session_id, seed.model_dump())

    registry = TrackingRegistry(
        {
            "project_architect": ExplodingArchitectAgent(),
            "execution_planner": FakeExecutionPlannerAgent(),
        }
    )
    orch = _make_orch(sm, seed, registry, _plan("project_architect", "execution_planner"), "architecture_design")
    response = await orch.process_request("Design and plan", session_id)

    assert "Issues:" in response["message"]
    assert "project_architect: failed_runtime" in response["message"]
    print("  PASS: failure summary stays visible in the user-facing orchestrator message")


@pytest.mark.asyncio
async def test_manual_mode_runs_selected_agent_without_downstream_expansion():
    """Manual mode should run the selected agent and not append downstream agents automatically."""
    session_id = "test-full-manual-architect"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)
    seed = ProjectState(
        session_id=session_id,
        current_phase="requirements_complete",
        requirements=Requirements(functional=["Auth"]),
    )
    await persistence.save(session_id, seed.model_dump())

    registry = TrackingRegistry(
        {
            "project_architect": FakeArchitectAgent(),
            "execution_planner": FakeExecutionPlannerAgent(),
        }
    )
    orch = _make_manual_orch(sm, registry)
    response = await orch.process_request(
        "Run architect only",
        session_id,
        agent_selection_mode="manual",
        selected_agent_id="project_architect",
    )

    assert response["intent"]["primary_intent"] == "manual"
    assert "project_architect" in registry.call_log
    assert "execution_planner" not in registry.call_log
    print("  PASS: manual mode runs the selected agent without downstream expansion")


@pytest.mark.asyncio
async def test_manual_mode_rejects_unavailable_agent_selection():
    """Manual mode should reject agents that are not ready in the current phase/state."""
    session_id = "test-full-manual-unavailable"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)
    seed = ProjectState(session_id=session_id, current_phase="initialization", requirements=Requirements())
    await persistence.save(session_id, seed.model_dump())

    registry = TrackingRegistry({"project_architect": FakeArchitectAgent()})
    orch = _make_manual_orch(sm, registry)
    response = await orch.process_request(
        "Run architect now",
        session_id,
        agent_selection_mode="manual",
        selected_agent_id="project_architect",
    )

    assert "unavailable" in response["message"]
    assert response["plan"] is None
    assert registry.call_log == []
    architect_entry = next(a for a in response["available_agents"] if a["agent_id"] == "project_architect")
    assert architect_entry["is_available"] is False
    assert architect_entry["unmet_requires"] == ["requirements"]
    print("  PASS: manual mode rejects unavailable agents with readiness details")


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tests = [
        test_full_orchestration_multi_turn,
        test_available_agents_include_readiness_metadata,
        test_phase_transition_map_covers_all_producing_agents,
        test_conversation_history_roles_always_alternate,
        test_agent_results_skipped_for_unimplemented_agents,
        test_export_artifacts_persist_when_exporter_runs,
        test_failure_message_surfaces_issue_summary,
        test_manual_mode_runs_selected_agent_without_downstream_expansion,
        test_manual_mode_rejects_unavailable_agent_selection,
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
