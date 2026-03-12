"""
Comprehensive end-to-end test for the full orchestrator.

Exercises the checkpointed multi-turn flow:
  - Turn 1: requirements gathering checkpoint
  - Turn 2: explicit continue to architecture
  - Turn 3: explicit continue to execution planner
  - Turn 4: explicit continue to mockup generation
  - Turn 5: explicit continue to exporter
  - Turn 6: manual mode agent selection

No real LLM required - uses fake agents and a mocked graph.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.orchestrator.agent_store import AGENT_STORE, get_agent_by_id
from src.orchestrator.execution_plan import ExecutionPlan
from src.orchestrator.master_agent import MasterOrchestrator, PHASE_TRANSITION_MAP
from src.protocols.schemas import RequirementsState
from src.state.project_state import ArchitectureDefinition, ProjectState, Requirements
from src.state.state_manager import StateManager
from src.storage.memory_store import InMemoryPersistenceAdapter


class FakeRequirementsCollector:
    def __init__(self, *, is_complete: bool = True, progress: float = 1.0):
        self.call_count = 0
        self._is_complete = is_complete
        self._progress = progress

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
                is_complete=self._is_complete,
                progress=self._progress,
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
        return {
            "state_delta": {
                "roadmap": {
                    "phases": [{"name": "Build", "description": "Core build", "order": 0}],
                    "milestones": [{"name": "M1", "description": "Initial milestone", "target_date": None}],
                    "implementation_tasks": [],
                    "sprints": [],
                    "critical_path": None,
                    "external_resources": [],
                }
            },
            "summary": "Execution plan ready.",
        }


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


class TrackingRegistry:
    def __init__(self, agents: dict):
        self._agents = agents
        self.call_log: list[str] = []

    def get_agent(self, agent_id: str):
        agent = self._agents.get(agent_id)
        if agent is not None:
            self.call_log.append(agent_id)
        return agent


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
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "project_state": project_state,
            "plan": plan,
            "intent": {
                "primary_intent": intent_label,
                "requires_agents": [task.agent_id for task in plan.tasks],
                "confidence": 0.9,
            },
            "error": None,
        }
    )
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


@pytest.mark.asyncio
async def test_full_orchestration_multi_turn():
    session_id = "test-full-e2e"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)

    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    fake_req = FakeRequirementsCollector()
    fake_arch = FakeArchitectAgent(tech_stack={"backend": "Python/FastAPI"})
    fake_exec = FakeExecutionPlannerAgent()
    fake_mockup = FakeMockupAgent()
    fake_exporter = FakeExporterAgent()

    registry1 = TrackingRegistry({"requirements_collector": fake_req})
    state1 = await sm.load(session_id)
    orch1 = _make_orch(sm, state1, registry1, _plan("requirements_collector"), "requirements_gathering")
    r1 = await orch1.process_request("I want to build a task management app", session_id)

    assert len(r1["available_agents"]) == len(AGENT_STORE)
    assert [ar["agent_id"] for ar in r1["agent_results"]] == ["requirements_collector"]
    assert r1["current_step"]["agent_id"] == "requirements_collector"
    assert r1["next_step"]["agent_id"] == "project_architect"
    assert r1["awaiting_user_action"] is True

    s1 = await persistence.get(session_id)
    assert s1["current_phase"] == "requirements_complete"
    assert s1["requirements"]["project_type"] == "web app"
    assert s1["requirements"]["is_complete"] is True
    assert s1["awaiting_user_action"] is True
    assert s1["next_recommended_agent_id"] == "project_architect"
    assert len(s1["conversation_history"]) == 2

    registry2 = TrackingRegistry({"project_architect": fake_arch, "execution_planner": fake_exec})
    state2 = ProjectState(**await persistence.get(session_id))
    orch2 = _make_orch(sm, state2, registry2, _plan("project_architect", "execution_planner"), "architecture_design")
    r2 = await orch2.process_request("continue", session_id)

    assert [ar["agent_id"] for ar in r2["agent_results"]] == ["project_architect"]
    assert r2["current_step"]["agent_id"] == "project_architect"
    assert r2["next_step"]["agent_id"] == "execution_planner"
    assert r2["awaiting_user_action"] is True

    s2 = await persistence.get(session_id)
    assert s2["current_phase"] == "architecture_complete"
    assert s2["next_recommended_agent_id"] == "execution_planner"
    assert s2["architecture"]["tech_stack"]["backend"] == "Python/FastAPI"
    assert len(s2["conversation_history"]) == 4

    registry3 = TrackingRegistry({"execution_planner": fake_exec, "mockup_agent": fake_mockup})
    state3 = ProjectState(**await persistence.get(session_id))
    orch3 = _make_orch(sm, state3, registry3, _plan("project_architect", "execution_planner"), "architecture_design")
    r3 = await orch3.process_request("continue", session_id)

    s3 = await persistence.get(session_id)
    assert r3["current_step"]["agent_id"] == "execution_planner"
    assert r3["next_step"]["agent_id"] == "mockup_agent"
    assert r3["awaiting_user_action"] is True
    assert s3["current_phase"] == "planning_complete"
    assert s3["last_completed_agent_id"] == "execution_planner"
    assert s3["next_recommended_agent_id"] == "mockup_agent"
    assert len(s3["conversation_history"]) == 6

    registry4 = TrackingRegistry({"mockup_agent": fake_mockup, "exporter": fake_exporter})
    state4 = ProjectState(**await persistence.get(session_id))
    orch4 = _make_orch(sm, state4, registry4, _plan("execution_planner", "mockup_agent"), "execution_planning")
    r4 = await orch4.process_request("continue", session_id)

    s4 = await persistence.get(session_id)
    assert r4["current_step"]["agent_id"] == "mockup_agent"
    assert r4["next_step"]["agent_id"] == "exporter"
    assert r4["awaiting_user_action"] is True
    assert s4["current_phase"] == "design_complete"
    assert s4["next_recommended_agent_id"] == "exporter"
    assert len(s4["conversation_history"]) == 8

    registry5 = TrackingRegistry({"exporter": fake_exporter})
    state5 = ProjectState(**await persistence.get(session_id))
    orch5 = _make_orch(sm, state5, registry5, _plan("mockup_agent", "exporter"), "mockup_creation")
    r5 = await orch5.process_request("continue", session_id)

    s5 = await persistence.get(session_id)
    assert r5["current_step"]["agent_id"] == "exporter"
    assert r5["next_step"] is None
    assert r5["awaiting_user_action"] is False
    assert s5["current_phase"] == "exportable"
    assert s5["export_artifacts"]["saved_path"] == "outputs/full-test-export.pdf"
    assert len(s5["conversation_history"]) == 10

    registry6 = TrackingRegistry({"requirements_collector": fake_req})
    orch6 = _make_manual_orch(sm, registry6)
    r6 = await orch6.process_request(
        "Re-collect requirements",
        session_id,
        agent_selection_mode="manual",
        selected_agent_id="requirements_collector",
    )

    assert r6["intent"]["primary_intent"] == "manual"
    assert "project_architect" not in registry6.call_log
    s6 = await persistence.get(session_id)
    assert s6["agent_selection_mode"] == "manual"
    assert s6["selected_agent_id"] == "requirements_collector"
    assert len(s6["conversation_history"]) == 12


@pytest.mark.asyncio
async def test_available_agents_include_readiness_metadata():
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


@pytest.mark.asyncio
async def test_phase_transition_map_covers_all_producing_agents():
    for entry in AGENT_STORE:
        if entry.get("produces"):
            assert entry["id"] in PHASE_TRANSITION_MAP


@pytest.mark.asyncio
async def test_conversation_history_roles_always_alternate():
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
        await orch.process_request(f"Message {i + 1}", session_id)

    s = await persistence.get(session_id)
    history = s["conversation_history"]
    assert len(history) == 6
    for i, entry in enumerate(history):
        expected_role = "user" if i % 2 == 0 else "assistant"
        assert entry["role"] == expected_role


@pytest.mark.asyncio
async def test_agent_results_skipped_for_unimplemented_agents():
    session_id = "test-full-skip"
    persistence = InMemoryPersistenceAdapter()
    sm = StateManager(persistence)
    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    registry = TrackingRegistry({})
    orch = _make_orch(sm, seed, registry, _plan("project_architect", "execution_planner"))
    r = await orch.process_request("Design and plan", session_id)

    skipped = [ar for ar in r["agent_results"] if ar["status"] == "skipped_unavailable"]
    assert any(ar["agent_id"] == "project_architect" for ar in skipped)


@pytest.mark.asyncio
async def test_export_artifacts_persist_when_exporter_runs():
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

    registry = TrackingRegistry({"exporter": FakeExporterAgent()})
    orch = _make_orch(sm, seed, registry, _plan("exporter"), "export")
    response = await orch.process_request("Export to PDF", session_id)

    persisted = await persistence.get(session_id)
    assert response["state_snapshot"]["export_artifacts"]["saved_path"] == "outputs/full-test-export.pdf"
    assert persisted["export_artifacts"]["generated_formats"] == ["markdown", "pdf"]
    assert persisted["export_artifacts"]["history"][0]["saved_path"] == "outputs/full-test-export.pdf"


@pytest.mark.asyncio
async def test_failure_message_surfaces_issue_summary():
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


@pytest.mark.asyncio
async def test_manual_mode_runs_selected_agent_without_downstream_expansion():
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


@pytest.mark.asyncio
async def test_manual_mode_rejects_unavailable_agent_selection():
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

    import asyncio

    async def run_all():
        print("\n=== Full Orchestration Test Suite ===")
        passed = 0
        for test in tests:
            print(f"Running {test.__name__}...")
            try:
                await test()
                passed += 1
            except AssertionError as exc:
                print(f"  FAIL: {exc}")
            except Exception as exc:
                import traceback

                print(f"  ERROR: {type(exc).__name__}: {exc}")
                traceback.print_exc()
        print(f"\nResults: {passed}/{len(tests)} passed")
        if passed < len(tests):
            raise SystemExit(1)

    asyncio.run(run_all())
