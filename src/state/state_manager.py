"""Manages CRUD operations on ProjectState instances."""

from __future__ import annotations

from typing import Dict

from src.state.project_state import ProjectState


class StateManager:
    """In-memory state manager for workflow state."""

    def __init__(self) -> None:
        self._states: Dict[str, ProjectState] = {}

    def create(self, state: ProjectState) -> None:
        """Store a new project state."""
        self._states[state.project_id] = state

    def get(self, project_id: str) -> ProjectState | None:
        """Retrieve a project state by ID."""
        return self._states.get(project_id)

    def update(self, project_id: str, updates: dict) -> ProjectState | None:
        """Update fields on a project state."""
        state = self._states.get(project_id)
        if not state:
            return None
        updated = state.model_copy(update=updates)
        self._states[project_id] = updated
        return updated

    def delete(self, project_id: str) -> None:
        """Remove a project state."""
        self._states.pop(project_id, None)
