"""
Project state across agent transitions: state is maintained, fed correctly to each agent, and updated after each step.

Uses a fake agent registry so we don't need real LLM; each fake agent returns a fixed state_delta.
Asserts:
- After each process_request, state_snapshot has the expected shape (requirements, architecture, roadmap, phase).
- Context fed to each agent includes prior agents' output (e.g. architect receives requirements from step 1).
- Phase advances correctly (requirements_complete -> architecture_complete -> planning_complete).
- Persisted state survives across requests (reload from persistence and assert).

Fake I/O matches real agents: requirements_collector returns RequirementsState + response/is_complete/progress;
architect returns state_delta with ArchitectureDefinition-shaped dict; execution_planner returns Roadmap.model_dump();
mockup_agent returns mockups as list of Mockup-shaped dicts; exporter returns object with .content and .state_delta.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import pytest

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.state.project_state import (
    ProjectState,
    Requirements,
    ArchitectureDefinition,
    Roadmap,
    Milestone,
    Phase,
    Mockup,
)
from src.state.state_manager import StateManager
from src.storage.memory_store import InMemoryPersistenceAdapter
from src.orchestrator.master_agent import MasterOrchestrator
from src.protocols.schemas import RequirementsState


# ----- Fake registry: agents that return fixed state_delta and record received context -----


class _FakeAgentRegistry:
    """Returns fake agents that emit predetermined state_delta and record the context they received."""

    def __init__(self, state_manager: Any):
        self._state_manager = state_manager
        self._cache: Dict[str, Any] = {}
        self.received: Dict[str, Any] = {}  # agent_id -> last payload/context

    def get_agent(self, agent_id: str) -> Any | None:
        if agent_id in self._cache:
            return self._cache[agent_id]
        agent = self._create_fake(agent_id)
        if agent:
            self._cache[agent_id] = agent
        return agent

    def _create_fake(self, agent_id: str) -> Any | None:
        received = self.received

        if agent_id == "requirements_collector":
            class FakeReq:
                async def process_message(self, user_message, current_requirements, conversation_history):
                    received["requirements_collector"] = {
                        "user_message": user_message,
                        "current_requirements": current_requirements.model_dump() if hasattr(current_requirements, "model_dump") else current_requirements,
                    }
                    rs = RequirementsState(
                        project_type="web app",
                        target_users=["solo user"],
                        key_features=["Auth", "Dashboard", "Search"],
                        technical_constraints=["Python backend", "React frontend"],
                        business_goals=["Stay organized"],
                        timeline="2 weeks",
                        budget="$0",
                        is_complete=True,
                        progress=0.9,
                    )
                    return {
                        "requirements": rs,
                        "response": "Thanks. I've captured that.",
                        "is_complete": True,
                        "progress": 0.9,
                        "decisions": [],
                        "assumptions": [],
                    }
            return FakeReq()

        if agent_id == "project_architect":
            # Real agent returns state_delta["architecture"] as dict matching ArchitectureDefinition
            class FakeArch:
                async def process(self, input_data):
                    received["project_architect"] = {
                        "requirements": input_data.get("requirements"),
                        "existing_architecture": input_data.get("existing_architecture"),
                        "user_request": input_data.get("user_request"),
                    }
                    arch_dict = ArchitectureDefinition(
                        tech_stack={"frontend": "React 18", "backend": "FastAPI", "database": "PostgreSQL"},
                        tech_stack_rationale="Fits requirements.",
                        system_diagram="flowchart TD\n  A[User] --> B[API]",
                    ).model_dump()
                    return {
                        "state_delta": {"architecture": arch_dict},
                        "summary": "Architecture generated.",
                    }
            return FakeArch()

        if agent_id == "execution_planner":
            # Real agent builds Phase/Milestone/Roadmap then returns roadmap.model_dump()
            class FakePlan:
                async def process(self, payload):
                    received["execution_planner"] = {
                        "requirements": payload.get("requirements"),
                        "architecture": payload.get("architecture"),
                        "existing_roadmap": payload.get("existing_roadmap"),
                        "user_request": payload.get("user_request"),
                    }
                    roadmap = Roadmap(
                        phases=[Phase(name="Setup", description="Initial setup", order=0)],
                        milestones=[Milestone(name="M1", description="First milestone", target_date=None)],
                        implementation_tasks=[],
                        sprints=[],
                        critical_path=None,
                        external_resources=[],
                    )
                    return {
                        "state_delta": {"roadmap": roadmap.model_dump()},
                        "summary": "Roadmap created.",
                    }
            return FakePlan()

        if agent_id == "mockup_agent":
            # Real agent returns state_delta["mockups"] as list of dicts matching Mockup (master_agent normalizes)
            class FakeMockup:
                async def process(self, payload):
                    received["mockup_agent"] = {
                        "requirements": payload.get("requirements"),
                        "architecture": payload.get("architecture"),
                        "platform": payload.get("platform"),
                        "user_request": payload.get("user_request"),
                    }
                    entry = Mockup(
                        screen_name="Login",
                        wireframe_code="{}",
                        user_flow="Login flow",
                        interactions=[],
                        screen_id="login",
                        template_used="auth",
                    ).model_dump()
                    return {
                        "state_delta": {"mockups": [entry]},
                        "summary": "Mockup generated.",
                    }
            return FakeMockup()

        if agent_id == "exporter":
            class FakeExporter:
                async def execute(self, payload, context=None, tools=None):
                    received["exporter"] = {
                        "payload_keys": list(payload.keys()) if isinstance(payload, dict) else [],
                        "has_requirements": "requirements" in (payload or {}),
                        "has_architecture": "architecture" in (payload or {}),
                        "has_roadmap": "roadmap" in (payload or {}),
                    }
                    class Out:
                        content = "Export complete."
                        state_delta = {
                            "export_artifacts": {
                                "executive_summary": "Export summary",
                                "markdown_content": "# Export",
                                "saved_path": "outputs/state-transition-export.pdf",
                                "generated_formats": ["markdown", "pdf"],
                                "exported_at": "2026-03-06T20:30:00",
                                "history": [
                                    {
                                        "saved_path": "outputs/state-transition-export.pdf",
                                        "generated_formats": ["markdown", "pdf"],
                                        "exported_at": "2026-03-06T20:30:00",
                                    }
                                ],
                            }
                        }
                    return Out()
            return FakeExporter()

        return None


# ----- Fixtures -----


@pytest.fixture
def persistence():
    return InMemoryPersistenceAdapter()


@pytest.fixture
def state_manager(persistence):
    return StateManager(persistence)


@pytest.fixture
def fake_registry(state_manager):
    return _FakeAgentRegistry(state_manager)


@pytest.fixture
def session_id():
    return "state-transition-session"


@pytest.fixture
async def seeded_initial_state(persistence, session_id):
    """Initial state: initialization phase, empty requirements."""
    state = ProjectState(
        session_id=session_id,
        current_phase="initialization",
        requirements=Requirements(),
    )
    await persistence.save(session_id, state.model_dump())
    return state


# ----- 1. Single step: requirements_collector updates state and phase -----


@pytest.mark.asyncio
async def test_after_requirements_step_state_updated_and_phase_advanced(
    state_manager, fake_registry, persistence, session_id, seeded_initial_state
):
    """Run requirements_collector; state has requirements and phase is requirements_complete."""
    orch = MasterOrchestrator(state_manager, agent_registry=fake_registry, use_llm=False)
    resp = await orch.process_request("I want to clarify our goals", session_id)
    assert resp.get("error") is None
    snap = resp.get("state_snapshot") or {}
    assert "requirements" in snap
    req = snap["requirements"]
    assert (req.get("functional") or req.get("key_features")) or (req.get("constraints") or req.get("technical_constraints")), "requirements should be populated"
    assert req.get("project_type") == "web app"
    assert req.get("target_users") == ["solo user"]
    assert req.get("business_goals") == ["Stay organized"]
    assert req.get("timeline") == "2 weeks"
    assert req.get("budget") == "$0"
    assert req.get("is_complete") is True
    assert req.get("progress") == pytest.approx(0.9)
    assert snap.get("current_phase") == "requirements_complete"
    assert resp.get("current_step", {}).get("agent_id") == "requirements_collector"
    assert resp.get("next_step", {}).get("agent_id") == "project_architect"
    assert resp.get("awaiting_user_action") is True
    assert "conversation_history" in snap
    assert len(snap["conversation_history"]) >= 2  # user + assistant


@pytest.mark.asyncio
async def test_after_requirements_step_persisted_state_has_requirements(
    state_manager, fake_registry, persistence, session_id, seeded_initial_state
):
    """After requirements step, reload from persistence and assert state has requirements and phase."""
    orch = MasterOrchestrator(state_manager, agent_registry=fake_registry, use_llm=False)
    await orch.process_request("clarify our goals", session_id)
    state_manager.cache.clear()
    reloaded = await state_manager.load(session_id)
    assert reloaded.current_phase == "requirements_complete"
    assert reloaded.requirements is not None
    assert reloaded.requirements.functional == ["Auth", "Dashboard", "Search"]
    assert reloaded.requirements.constraints == ["Python backend", "React frontend"]
    assert reloaded.requirements.project_type == "web app"
    assert reloaded.requirements.target_users == ["solo user"]
    assert reloaded.requirements.business_goals == ["Stay organized"]
    assert reloaded.requirements.timeline == "2 weeks"
    assert reloaded.requirements.budget == "$0"
    assert reloaded.requirements.is_complete is True
    assert reloaded.requirements.progress == pytest.approx(0.9)
    assert reloaded.awaiting_user_action is True
    assert reloaded.next_recommended_agent_id == "project_architect"


# ----- 2. Two-step: requirements then architecture; state fed and updated -----


@pytest.mark.asyncio
async def test_transition_requirements_then_architecture_state_fed_and_updated(
    state_manager, fake_registry, persistence, session_id
):
    """Step 1: requirements. Step 2: architecture. Architect receives requirements; state has both and phase architecture_complete."""
    seed = ProjectState(
        session_id=session_id,
        current_phase="initialization",
        requirements=Requirements(),
    )
    await persistence.save(session_id, seed.model_dump())
    orch = MasterOrchestrator(state_manager, agent_registry=fake_registry, use_llm=False)

    r1 = await orch.process_request("I want to clarify our goals", session_id)
    assert r1.get("state_snapshot", {}).get("current_phase") == "requirements_complete"
    assert r1.get("next_step", {}).get("agent_id") == "project_architect"

    r2 = await orch.process_request("continue", session_id)
    assert r2.get("error") is None
    snap2 = r2.get("state_snapshot") or {}
    assert snap2.get("current_phase") == "architecture_complete"
    assert "architecture" in snap2
    arch = snap2["architecture"]
    assert arch.get("tech_stack") or arch.get("system_diagram"), "architecture should have content"

    # Architect was fed requirements from step 1
    received = fake_registry.received.get("project_architect")
    assert received is not None
    req_fed = received.get("requirements")
    assert req_fed is not None
    assert req_fed.get("functional") or req_fed.get("key_features"), "architect should have received requirements from previous step"
    assert req_fed.get("target_users") == ["solo user"]
    assert req_fed.get("business_goals") == ["Stay organized"]


@pytest.mark.asyncio
async def test_transition_architecture_then_roadmap_state_fed_and_updated(
    state_manager, fake_registry, persistence, session_id
):
    """Start from requirements_complete + minimal requirements. Run architect then roadmap. Planner receives architecture; state has roadmap and phase planning_complete."""
    seed = ProjectState(
        session_id=session_id,
        current_phase="requirements_complete",
        requirements=Requirements(functional=["Auth"], constraints=["Python"]),
    )
    await persistence.save(session_id, seed.model_dump())
    orch = MasterOrchestrator(state_manager, agent_registry=fake_registry, use_llm=False)

    r1 = await orch.process_request("generate the architecture", session_id)
    snap1 = r1.get("state_snapshot") or {}
    assert snap1.get("current_phase") == "architecture_complete"
    assert snap1.get("architecture", {}).get("tech_stack")
    assert r1.get("next_step", {}).get("agent_id") == "execution_planner"

    r2 = await orch.process_request("continue", session_id)
    assert r2.get("error") is None
    snap2 = r2.get("state_snapshot") or {}
    assert snap2.get("current_phase") == "planning_complete"
    assert "roadmap" in snap2
    roadmap = snap2["roadmap"]
    assert roadmap.get("phases") or roadmap.get("milestones"), "roadmap should have content"

    received = fake_registry.received.get("execution_planner")
    assert received is not None
    arch_fed = received.get("architecture")
    assert arch_fed is not None
    assert arch_fed.get("tech_stack"), "execution_planner should have received architecture from previous step"


# ----- 3. Full chain: requirements -> architecture -> roadmap -> mockup -> export -----


@pytest.mark.asyncio
async def test_full_chain_state_maintained_and_phase_advances(
    state_manager, fake_registry, persistence, session_id
):
    """Run a full chain of intents; after each step state accumulates and phase advances; exporter receives full state."""
    seed = ProjectState(
        session_id=session_id,
        current_phase="initialization",
        requirements=Requirements(),
    )
    await persistence.save(session_id, seed.model_dump())
    orch = MasterOrchestrator(state_manager, agent_registry=fake_registry, use_llm=False)

    await orch.process_request("clarify our goals", session_id)
    await orch.process_request("generate architecture", session_id)
    await orch.process_request("give me a roadmap", session_id)
    await orch.process_request("create wireframes", session_id)
    r_export = await orch.process_request("export to PDF", session_id)

    snap = r_export.get("state_snapshot") or {}
    assert snap.get("requirements") is not None or "requirements" in str(snap)
    assert snap.get("architecture") is not None
    assert snap.get("roadmap") is not None
    assert snap.get("mockups") is not None and len(snap.get("mockups", [])) >= 1
    assert snap.get("current_phase") == "design_complete" or snap.get("current_phase") == "exportable"
    assert snap.get("export_artifacts", {}).get("saved_path") == "outputs/state-transition-export.pdf"
    assert snap.get("export_artifacts", {}).get("generated_formats") == ["markdown", "pdf"]

    received = fake_registry.received.get("exporter")
    assert received is not None
    assert received.get("has_requirements") or "requirements" in received.get("payload_keys", [])
    assert received.get("has_architecture")
    assert received.get("has_roadmap")


# ----- 4. Reload from persistence after full chain -----


@pytest.mark.asyncio
async def test_after_full_chain_reloaded_state_complete(
    state_manager, fake_registry, persistence, session_id
):
    """After full chain, reload persisted requirements, architecture, roadmap, mockups, and export metadata."""
    seed = ProjectState(
        session_id=session_id,
        current_phase="initialization",
        requirements=Requirements(),
    )
    await persistence.save(session_id, seed.model_dump())
    orch = MasterOrchestrator(state_manager, agent_registry=fake_registry, use_llm=False)
    await orch.process_request("goals", session_id)
    await orch.process_request("architecture", session_id)
    await orch.process_request("roadmap", session_id)
    await orch.process_request("wireframes", session_id)
    await orch.process_request("export", session_id)

    state_manager.cache.clear()
    reloaded = await state_manager.load(session_id)
    assert reloaded.current_phase in ("design_complete", "planning_complete", "architecture_complete", "exportable")
    assert reloaded.requirements is not None
    assert reloaded.architecture is not None and (reloaded.architecture.tech_stack or reloaded.architecture.system_diagram)
    assert reloaded.roadmap is not None and (reloaded.roadmap.phases or reloaded.roadmap.milestones)
    assert reloaded.mockups is not None and len(reloaded.mockups) >= 1
    assert reloaded.export_artifacts.saved_path == "outputs/state-transition-export.pdf"
    assert reloaded.export_artifacts.generated_formats == ["markdown", "pdf"]
    assert len(reloaded.export_artifacts.history) == 1


@pytest.mark.asyncio
async def test_repeated_mockup_generation_replaces_same_screen_without_duplicates(
    state_manager, fake_registry, persistence, session_id
):
    """Two mockup generations for the same screen_id should keep one stored mockup entry."""
    seed = ProjectState(
        session_id=session_id,
        current_phase="architecture_complete",
        requirements=Requirements(functional=["Login"]),
        architecture=ArchitectureDefinition(tech_stack={"frontend": "React"}),
    )
    await persistence.save(session_id, seed.model_dump())
    orch = MasterOrchestrator(state_manager, agent_registry=fake_registry, use_llm=False)

    await orch.process_request("create wireframes", session_id)
    second = await orch.process_request("create wireframes again", session_id)

    snap = second.get("state_snapshot") or {}
    mockups = snap.get("mockups") or []
    assert len(mockups) == 1
    assert mockups[0].get("screen_id") == "login"

    state_manager.cache.clear()
    reloaded = await state_manager.load(session_id)
    assert len(reloaded.mockups) == 1
    assert reloaded.mockups[0].screen_id == "login"
