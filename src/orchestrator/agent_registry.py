"""Agent registry: get_agent(agent_id) returns runnable agent or None."""

from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)


class AgentRegistry:
    """Lazy-loaded registry for orchestrator agents. Requires state_manager for agents that need it."""

    def __init__(self, state_manager: Any):
        self._state_manager = state_manager
        self._cache: dict[str, Any] = {}
        self._runtime_llm: dict[str, str | None] | None = None

    def set_runtime_llm_config(self, api_key: str | None, model: str | None) -> None:
        """Set per-request key/model override."""
        self._runtime_llm = {
            "api_key": (api_key or "").strip() or None,
            "model": (model or "").strip() or None,
        }

    def clear_runtime_llm_config(self) -> None:
        """Clear per-request key/model override."""
        self._runtime_llm = None

    def get_agent(self, agent_id: str) -> Any | None:
        """Return agent instance for agent_id, or None if not implemented. Lazy init and cache."""
        # Runtime override builds fresh per-request instances (no cache reuse).
        if self._runtime_llm and self._runtime_llm.get("api_key"):
            return self._create_agent(agent_id)
        if agent_id in self._cache:
            return self._cache[agent_id]
        agent = self._create_agent(agent_id)
        if agent is not None:
            self._cache[agent_id] = agent
        return agent

    def _make_gemini_client(self) -> Any | None:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from src.services.llm_settings_service import normalize_gemini_model_id
            from src.utils.config import get_settings

            settings = get_settings()
            runtime = self._runtime_llm or {}
            api_key = runtime.get("api_key") or getattr(settings, "gemini_api_key", None)
            raw_model = runtime.get("model") or getattr(settings, "model_name", "gemini-2.5-flash")
            model = normalize_gemini_model_id(str(raw_model or "")) or raw_model
            if not api_key:
                return None
            return ChatGoogleGenerativeAI(
                model=model,
                temperature=0.2,
                google_api_key=api_key,
            )
        except Exception as exc:
            _log.warning("Failed to create Gemini client: %s", exc)
            return None

    def _create_agent(self, agent_id: str) -> Any | None:
        if agent_id == "requirements_collector":
            try:
                llm = self._make_gemini_client()
                if llm is None:
                    _log.warning("requirements_collector unavailable: no Gemini API key configured")
                    return None
                from src.agents.requirements_collector import RequirementsAgent
                return RequirementsAgent(llm_client=llm)
            except Exception as exc:
                _log.warning("Failed to create requirements_collector: %s", exc)
                return None

        if agent_id == "project_architect":
            try:
                from src.agents.project_architect import ProjectArchitectAgent
                llm = self._make_gemini_client()
                if llm is None:
                    return None
                return ProjectArchitectAgent(state_manager=self._state_manager, llm_client=llm)
            except Exception as exc:
                _log.warning("Failed to create project_architect: %s", exc)
                return None

        if agent_id == "execution_planner":
            try:
                from src.agents.execution_planner_agent import ExecutionPlannerAgent
                llm = self._make_gemini_client()
                return ExecutionPlannerAgent(state_manager=self._state_manager, llm_client=llm)
            except Exception as exc:
                _log.warning("Failed to create execution_planner: %s", exc)
                return None

        if agent_id == "mockup_agent":
            try:
                from src.agents.mockup_agent import MockupAgent
                llm = self._make_gemini_client()
                return MockupAgent(state_manager=self._state_manager, llm_client=llm)
            except Exception:
                # Mockup agent supports llm_client=None fallback mode.
                try:
                    from src.agents.mockup_agent import MockupAgent
                    return MockupAgent(state_manager=self._state_manager, llm_client=None)
                except Exception as exc:
                    _log.warning("Failed to create mockup_agent: %s", exc)
                    return None

        if agent_id == "exporter":
            try:
                from src.agents.exporter_agent import ExporterAgent, get_agent

                llm = self._make_gemini_client()
                if llm is not None:
                    return ExporterAgent(llm_client=llm)
                return get_agent()
            except Exception as exc:
                _log.warning("Failed to create exporter: %s", exc)
                return None

        return None

