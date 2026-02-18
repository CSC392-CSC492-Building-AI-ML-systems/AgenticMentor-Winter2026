"""LangGraph orchestrator flow: load_state → classify_intent → build_plan."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from src.orchestrator.execution_plan import ExecutionPlan
from src.orchestrator.intent_classifier import IntentResult


class OrchestratorState(TypedDict, total=False):
    """State for the orchestrator LangGraph."""
    user_input: str
    session_id: str
    project_state: Any
    intent: IntentResult
    plan: ExecutionPlan
    error: str


def build_orchestrator_graph(
    state_manager: Any,
    intent_classifier: Any,
    execution_planner: Any,
):
    """
    Build and compile the orchestrator LangGraph.

    Nodes: load_state → classify_intent → build_plan → END.
    Dependencies: state_manager (async load), intent_classifier (analyze_async),
    execution_planner (plan).
    """
    state_type = OrchestratorState

    async def load_state_node(state: OrchestratorState) -> dict:
        session_id = state.get("session_id") or ""
        try:
            project_state = await state_manager.load(session_id)
            return {"project_state": project_state, "error": None}
        except Exception as e:
            return {"project_state": None, "error": str(e)}

    async def classify_intent_node(state: OrchestratorState) -> dict:
        if state.get("error"):
            return {}
        user_input = (state.get("user_input") or "").strip()
        project_state = state.get("project_state")
        current_phase = getattr(project_state, "current_phase", "initialization") if project_state else "initialization"
        if hasattr(intent_classifier, "analyze_async"):
            intent = await intent_classifier.analyze_async(user_input, current_phase)
        else:
            intent = intent_classifier.analyze(user_input, current_phase)
        return {"intent": intent}

    async def build_plan_node(state: OrchestratorState) -> dict:
        if state.get("error"):
            return {}
        intent = state.get("intent")
        project_state = state.get("project_state")
        if not intent or not project_state:
            return {"plan": ExecutionPlan(tasks=[])}
        plan = execution_planner.plan(intent, project_state)
        return {"plan": plan}

    graph = StateGraph(state_type)
    graph.add_node("load_state", load_state_node)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("build_plan", build_plan_node)

    graph.set_entry_point("load_state")
    graph.add_edge("load_state", "classify_intent")
    graph.add_edge("classify_intent", "build_plan")
    graph.add_edge("build_plan", END)

    return graph.compile()


__all__ = ["OrchestratorState", "build_orchestrator_graph"]
