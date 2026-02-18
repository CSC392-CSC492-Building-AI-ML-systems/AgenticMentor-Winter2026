"""Master orchestrator: LangGraph flow (load → classify → build_plan) with optional LangChain LLM intent."""

from __future__ import annotations

from typing import Any

from src.orchestrator.agent_store import AGENT_STORE
from src.orchestrator.execution_planner import ExecutionPlanner
from src.orchestrator.graph import build_orchestrator_graph
from src.orchestrator.intent_classifier import IntentClassifier


def _make_llm_if_configured() -> Any:
    """Build a LangChain ChatGoogleGenerativeAI if Gemini API key is set; else None."""
    try:
        from src.utils.config import get_settings
        from langchain_google_genai import ChatGoogleGenerativeAI
        s = get_settings()
        if getattr(s, "gemini_api_key", None):
            return ChatGoogleGenerativeAI(
                model=getattr(s, "model_name", "gemini-2.0-flash"),
                temperature=getattr(s, "model_temperature", 0.2),
                api_key=s.gemini_api_key,
            )
    except Exception:
        pass
    return None


class MasterOrchestrator:
    """Orchestrator using LangGraph (load_state → classify_intent → build_plan) and optional LangChain LLM for intent."""

    def __init__(self, state_manager: Any, agent_registry: Any = None, *, use_llm: bool = True):
        self.state = state_manager
        self.agents = agent_registry or AGENT_STORE
        llm = _make_llm_if_configured() if use_llm else None
        self.intent_classifier = IntentClassifier(llm=llm)
        self.execution_planner = ExecutionPlanner()
        self._graph = build_orchestrator_graph(
            state_manager=self.state,
            intent_classifier=self.intent_classifier,
            execution_planner=self.execution_planner,
        )

    async def process_request(self, user_input: str, session_id: str) -> dict:
        """
        Run the orchestrator LangGraph and return state (intent, plan, project_state, error).
        Does not execute agents yet (Branch 1: plan only).
        """
        initial = {
            "user_input": user_input or "",
            "session_id": session_id or "",
        }
        result = await self._graph.ainvoke(initial)
        return dict(result)

    def _build_execution_plan(self, intent: Any, project_state: Any) -> Any:
        """Build plan from intent and state (used if not using graph)."""
        return self.execution_planner.plan(intent, project_state)
