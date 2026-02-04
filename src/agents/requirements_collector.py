"""Collects and normalizes project requirements from user input."""

from __future__ import annotations

from src.agents.base_agent import BaseAgent


class RequirementsCollector(BaseAgent):
    """Agent that gathers requirements and constraints."""

    def run(self, payload: dict) -> dict:
        """Extract and return requirement details."""
        return {"requirements": payload.get("raw_input", "")}
