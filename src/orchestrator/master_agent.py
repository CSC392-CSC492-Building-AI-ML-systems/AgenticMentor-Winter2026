"""Master orchestrator: LangGraph flow (load → classify → build_plan) with optional LangChain LLM intent."""

from __future__ import annotations

from typing import Any

from src.orchestrator.agent_registry import AgentRegistry
from src.orchestrator.agent_store import AGENT_STORE, get_agent_by_id
from src.orchestrator.execution_plan import Task
from src.orchestrator.execution_planner import ExecutionPlanner
from src.orchestrator.graph import build_orchestrator_graph
from src.orchestrator.intent_classifier import IntentClassifier

# Maps agent_id → the phase that becomes active after that agent completes.
PHASE_TRANSITION_MAP: dict[str, str] = {
    "requirements_collector": "requirements_complete",
    "project_architect": "architecture_complete",
    "execution_planner": "planning_complete",
    "mockup_agent": "design_complete",
    "exporter": "exportable",
}


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
        self.registry = agent_registry if agent_registry is not None else AgentRegistry(state_manager)
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
        Load state, classify intent, build plan, run each task, synthesize, return response.
        """
        initial = {"user_input": user_input or "", "session_id": session_id or ""}
        graph_result = await self._graph.ainvoke(initial)
        error = graph_result.get("error")
        if error:
            return {
                "message": f"Error: {error}",
                "state_snapshot": None,
                "artifacts": [],
                "intent": None,
                "plan": graph_result.get("plan"),
                "project_state": None,
            }
        plan = graph_result.get("plan")
        project_state = graph_result.get("project_state")
        intent = graph_result.get("intent")
        if not plan or not plan.tasks or not project_state:
            return {
                "message": "No plan or state.",
                "state_snapshot": project_state.model_dump() if project_state else None,
                "artifacts": [],
                "intent": intent,
                "plan": plan,
                "project_state": project_state,
            }
        results = []
        for task in plan.tasks:
            agent = self.registry.get_agent(task.agent_id) if hasattr(self.registry, "get_agent") else None
            if agent is None:
                continue
            context = self._extract_context(project_state, task.required_context)
            result = await self._run_agent(task, context, user_input or "", agent)
            if not result:
                continue
            state_delta = result.get("state_delta") or {}
            if state_delta:
                project_state = await self.state.update(session_id, state_delta)
            # 3.2 Phase transition: update current_phase after agent completes.
            next_phase = PHASE_TRANSITION_MAP.get(task.agent_id)
            if next_phase:
                project_state = await self.state.update(session_id, {"current_phase": next_phase})
            results.append(result)
        message = self._synthesize_response(results)
        # 3.3 Conversation history: append user + assistant turns and persist.
        # We set the field directly (bypassing StateManager's list-extend merge)
        # so re-running process_request never double-appends old entries.
        new_history = list(project_state.conversation_history or [])
        new_history.append({"role": "user", "content": user_input or ""})
        new_history.append({"role": "assistant", "content": message})
        project_state.conversation_history = new_history
        await self.state.db.save(session_id, project_state.model_dump())
        self.state.cache[session_id] = project_state
        return {
            "message": message,
            "state_snapshot": project_state.model_dump() if project_state else None,
            "artifacts": results,
            "intent": graph_result.get("intent"),
            "plan": plan,
            "project_state": project_state,
        }

    def _extract_context(self, project_state: Any, required_context: list[str]) -> dict:
        """Build context dict from project_state for the given keys; '*' means full state."""
        if not required_context or ("*" in required_context):
            return project_state.model_dump() if hasattr(project_state, "model_dump") else {}
        out = {}
        for key in required_context:
            if "." in key:
                val = project_state
                for part in key.split("."):
                    val = getattr(val, part, None) if not isinstance(val, dict) else val.get(part)
                out[key] = val
            else:
                val = getattr(project_state, key, None)
                out[key] = val.model_dump() if hasattr(val, "model_dump") else val
        return out

    async def _run_agent(self, task: Task, context: dict, user_input: str, agent: Any) -> dict | None:
        """Run agent for task; return { state_delta, content } or None."""
        agent_id = task.agent_id
        try:
            if agent_id == "project_architect":
                req = context.get("requirements")
                req_dict = req if isinstance(req, dict) else (req.model_dump() if hasattr(req, "model_dump") else {})
                input_data = {
                    "requirements": req_dict,
                    "existing_architecture": context.get("architecture"),
                    "user_request": user_input,
                }
                raw = await agent.process(input_data)
                state_delta = raw.get("state_delta") or {}
                if not state_delta and raw.get("architecture") is not None:
                    state_delta = {"architecture": raw["architecture"]}
                return {"state_delta": state_delta, "content": raw.get("summary") or ""}
            if agent_id == "requirements_collector":
                from src.protocols.schemas import RequirementsState
                req = context.get("requirements")
                if isinstance(req, dict):
                    rs = RequirementsState(
                        key_features=(req.get("functional") or []) + (req.get("non_functional") or []),
                        technical_constraints=req.get("constraints") or [],
                    )
                else:
                    rs = RequirementsState(
                        key_features=(getattr(req, "functional", []) or []) + (getattr(req, "non_functional", []) or []),
                        technical_constraints=getattr(req, "constraints", []) or [],
                    ) if req else RequirementsState()
                history = context.get("conversation_history") or []
                raw = await agent.process_message(user_input, rs, history)
                req_out = raw.get("requirements")
                if req_out is None:
                    return {"state_delta": {}, "content": raw.get("response") or ""}
                rs_dump = req_out.model_dump() if hasattr(req_out, "model_dump") else {}
                state_delta = {
                    "requirements": {
                        "functional": rs_dump.get("key_features", []) or [],
                        "non_functional": [],
                        "constraints": rs_dump.get("technical_constraints", []) or [],
                        "user_stories": [],
                        "gaps": [],
                    }
                }
                return {"state_delta": state_delta, "content": raw.get("response") or ""}

            # --- Placeholders: add adapter logic here when agents are implemented ---

            if agent_id == "execution_planner":
                # TODO: wire ExecutionPlannerAgent when built.
                # Expected input:  {"architecture": context.get("architecture"), "user_request": user_input}
                # Expected output: {"state_delta": {"roadmap": {...}}, "content": "..."}
                return None  # skipped until agent is implemented

            if agent_id == "mockup_agent":
                # TODO: wire MockupAgent when built.
                # Expected input:  {"requirements": context.get("requirements"), "architecture": context.get("architecture"), "user_request": user_input}
                # Expected output: {"state_delta": {"mockups": [...]}, "content": "..."}
                return None  # skipped until agent is implemented

            if agent_id == "exporter":
                # TODO: wire ExporterAgent when built.
                # Expected input:  full context (required_context = ["*"])
                # Expected output: {"state_delta": {}, "content": "Export ready at <path>"}
                return None  # skipped until agent is implemented

        except Exception:
            return None
        return None

    def _synthesize_response(self, results: list[dict]) -> str:
        """Turn agent results into one user-facing message."""
        if not results:
            return "No agents ran."
        parts = []
        for r in results:
            c = r.get("content") or r.get("summary") or ""
            if c:
                parts.append(c.strip())
        return " ".join(parts) if parts else "Done."
