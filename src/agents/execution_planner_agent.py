"""Creates a detailed execution plan across specialized agents."""

from __future__ import annotations

from src.agents.base_agent import BaseAgent


class ExecutionPlannerAgent(BaseAgent):
    """Agent responsible for task planning."""

    def run(self, payload: dict) -> dict:
        """Return a placeholder execution plan."""
        return {"plan": ["step_one", "step_two"]}
