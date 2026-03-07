"""Unit tests for StateManager merge/revalidation behavior."""

from __future__ import annotations

import pytest

from src.state.project_state import Milestone, Phase, ProjectState
from src.state.state_manager import StateManager
from src.storage.memory_store import InMemoryPersistenceAdapter


@pytest.mark.asyncio
async def test_update_revalidates_nested_roadmap_models():
    """Updating roadmap with a dict should rebuild nested Phase/Milestone models."""
    session_id = "state-manager-roadmap-types"
    sm = StateManager(InMemoryPersistenceAdapter())

    state = await sm.update(
        session_id,
        {
            "roadmap": {
                "phases": [{"name": "Setup", "description": "Init", "order": 0}],
                "milestones": [{"name": "M1", "description": "First", "target_date": None}],
                "implementation_tasks": [],
                "sprints": [],
                "critical_path": None,
                "external_resources": [],
            }
        },
    )

    assert len(state.roadmap.phases) == 1
    assert isinstance(state.roadmap.phases[0], Phase)
    assert state.roadmap.phases[0].name == "Setup"
    assert len(state.roadmap.milestones) == 1
    assert isinstance(state.roadmap.milestones[0], Milestone)
    assert state.roadmap.milestones[0].name == "M1"


@pytest.mark.asyncio
async def test_roadmap_replacement_does_not_duplicate_phase_lists():
    """Sequential full-roadmap updates should replace phases, not append duplicates."""
    session_id = "state-manager-roadmap-replace"
    sm = StateManager(InMemoryPersistenceAdapter())

    await sm.update(
        session_id,
        {
            "roadmap": {
                "phases": [{"name": "Setup", "description": "Init", "order": 0}],
                "milestones": [],
                "implementation_tasks": [],
                "sprints": [],
                "critical_path": None,
                "external_resources": [],
            }
        },
    )

    state = await sm.update(
        session_id,
        {
            "roadmap": {
                "phases": [{"name": "Build", "description": "Core build", "order": 1}],
                "milestones": [],
                "implementation_tasks": [],
                "sprints": [],
                "critical_path": None,
                "external_resources": [],
            }
        },
    )

    assert len(state.roadmap.phases) == 1
    assert state.roadmap.phases[0].name == "Build"
