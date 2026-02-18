"""E2E test: MasterOrchestrator with AgentRegistry runs plan and updates state."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.state.project_state import ProjectState, Requirements
from src.state.state_manager import StateManager
from src.storage.memory_store import InMemoryPersistenceAdapter
from src.orchestrator.master_agent import MasterOrchestrator


# Skip E2E that calls Gemini if no API key (e.g. in CI)
SKIP_REAL_LLM = not os.environ.get("GEMINI_API_KEY") and not os.environ.get("gemini_api_key")


@pytest.mark.asyncio
@pytest.mark.skipif(SKIP_REAL_LLM, reason="GEMINI_API_KEY not set; E2E uses real ProjectArchitectAgent")
async def test_orchestrator_e2e_generate_architecture():
    """In-memory persistence, seeded requirements, process_request('generate architecture') -> state has architecture, non-empty message."""
    session_id = "e2e-session-1"
    persistence = InMemoryPersistenceAdapter()
    state_manager = StateManager(persistence)

    # Seed state: minimal requirements + phase so intent matches architecture_design
    seed = ProjectState(
        session_id=session_id,
        current_phase="requirements_complete",
        requirements=Requirements(
            functional=["User authentication", "Dashboard for activity"],
            non_functional=[],
            constraints=["Python backend"],
        ),
    )
    await persistence.save(session_id, seed.model_dump())

    orchestrator = MasterOrchestrator(state_manager, use_llm=False)

    response = await orchestrator.process_request("generate architecture", session_id)

    assert "message" in response
    assert response["message"], "Expected non-empty user-facing message"
    state_snapshot = response.get("state_snapshot")
    assert state_snapshot is not None, "Expected state_snapshot in response"
    arch = state_snapshot.get("architecture") or {}
    assert arch, "Expected architecture in state after running project_architect"
    # At least one of these is usually populated by the architect
    assert (
        arch.get("tech_stack")
        or arch.get("tech_stack_rationale")
        or arch.get("data_schema")
        or arch.get("system_diagram")
        or arch.get("api_design")
    ), "Expected architecture to have some content (tech_stack, rationale, schema, diagram, or api_design)"


@pytest.mark.asyncio
async def test_orchestrator_e2e_no_llm_plan_only():
    """Without Gemini: orchestrator still loads state, classifies intent, builds plan; no agent runs so no architecture."""
    session_id = "e2e-session-plan-only"
    persistence = InMemoryPersistenceAdapter()
    state_manager = StateManager(persistence)
    seed = ProjectState(
        session_id=session_id,
        current_phase="requirements_complete",
        requirements=Requirements(functional=["Auth"], constraints=[]),
    )
    await persistence.save(session_id, seed.model_dump())

    orchestrator = MasterOrchestrator(state_manager, use_llm=False)

    # If project_architect is in the plan but we skip real LLM, we'd need a mock. Here we run
    # with real registry; if GEMINI_API_KEY is set the agent runs, else it may still run and fail
    # or we skip the test above. This test runs always: just check that process_request returns
    # the expected shape (message, state_snapshot, artifacts).
    response = await orchestrator.process_request("generate architecture", session_id)

    assert "message" in response
    assert "state_snapshot" in response
    assert "artifacts" in response
    # If no API key, project_architect might raise; then we might get error or empty. Just check shape.
    if not response.get("message", "").startswith("Error:"):
        assert isinstance(response["artifacts"], list)
