"""Builds high-level architecture recommendations."""

from __future__ import annotations

from src.agents.base_agent import BaseAgent


class ProjectArchitect(BaseAgent):
    """Agent that proposes system architecture."""

    def run(self, payload: dict) -> dict:
        """Return a placeholder architecture blueprint."""
        return {"architecture": "proposed_architecture"}
