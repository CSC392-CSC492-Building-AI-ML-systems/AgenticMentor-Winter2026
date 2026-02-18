"""Agent registry: get_agent(agent_id) returns runnable agent or None."""

from __future__ import annotations

from typing import Any


class AgentRegistry:
    """Lazy-loaded registry for orchestrator agents. Requires state_manager for agents that need it."""

    def __init__(self, state_manager: Any):
        self._state_manager = state_manager
        self._cache: dict[str, Any] = {}

    def get_agent(self, agent_id: str) -> Any | None:
        """Return agent instance for agent_id, or None if not implemented. Lazy init and cache."""
        if agent_id in self._cache:
            return self._cache[agent_id]
        agent = self._create_agent(agent_id)
        if agent is not None:
            self._cache[agent_id] = agent
        return agent

    def _create_agent(self, agent_id: str) -> Any | None:
        if agent_id == "requirements_collector":
            from src.agents.requirements_collector import get_agent
            return get_agent()
        if agent_id == "project_architect":
            from src.adapters.llm_clients import GeminiClient
            from src.agents.project_architect import ProjectArchitectAgent
            llm = GeminiClient(model="gemini-2.0-flash", temperature=0.2)
            return ProjectArchitectAgent(state_manager=self._state_manager, llm_client=llm)
        return None
