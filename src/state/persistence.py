"""Persistence adapter for workflow state storage."""

from __future__ import annotations

from src.state.project_state import ProjectState


class PersistenceAdapter:
    """Adapter for SQLite/PostgreSQL persistence (placeholder)."""

    def save(self, state: ProjectState) -> None:
        """Persist a ProjectState instance."""
        return None

    def load(self, project_id: str) -> ProjectState | None:
        """Load a ProjectState instance by ID."""
        return None
