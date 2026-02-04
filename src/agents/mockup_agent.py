"""Generates UI/UX mockups or wireframes."""

from __future__ import annotations

from src.agents.base_agent import BaseAgent


class MockupAgent(BaseAgent):
    """Agent that produces mockup artifacts."""

    def run(self, payload: dict) -> dict:
        """Return a placeholder mockup reference."""
        return {"mockup": "mockup_placeholder"}
