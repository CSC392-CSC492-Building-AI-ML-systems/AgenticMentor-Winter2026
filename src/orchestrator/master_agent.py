"""Master orchestrator: LangGraph flow (load → classify → build_plan) with optional LangChain LLM intent."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from src.orchestrator.agent_registry import AgentRegistry
from src.orchestrator.agent_store import AGENT_STORE, get_agent_by_id, get_producer_for_artifact
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

AGENT_TIMEOUT_SECONDS: dict[str, float] = {
    "requirements_collector": 45.0,
    "project_architect": 150.0,
    "execution_planner": 90.0,
    "mockup_agent": 150.0,
    "exporter": 90.0,
}


def _make_llm_if_configured() -> Any:
    """Build a LangChain ChatGoogleGenerativeAI if Gemini API key is set; else None."""
    try:
        from src.utils.config import get_settings
        from langchain_google_genai import ChatGoogleGenerativeAI
        s = get_settings()
        if getattr(s, "gemini_api_key", None):
            return ChatGoogleGenerativeAI(
                model=getattr(s, "model_name", "gemini-2.5-flash"),
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

    async def process_request(
        self,
        user_input: str,
        session_id: str,
        *,
        agent_selection_mode: str = "auto",
        selected_agent_id: str | None = None,
    ) -> dict:
        """
        Load state, classify intent (auto) or use selected agent (manual),
        build plan, run each task, synthesize, return response.

        Args:
            user_input: Raw user message.
            session_id: Session identifier.
            agent_selection_mode: "auto" (default) or "manual".
            selected_agent_id: Required when mode is "manual"; the agent to run.
        """
        initial = {"user_input": user_input or "", "session_id": session_id or ""}

        # --- 3.4 Manual mode: bypass graph, build plan directly ---
        if agent_selection_mode == "manual" and selected_agent_id:
            project_state = await self.state.load(session_id)
            if project_state is None:
                return {"message": "Session not found.", "state_snapshot": None, "artifacts": [], "intent": None, "plan": None, "project_state": None, "agent_results": [], "available_agents": []}
            available_agents = self._get_available_agents(project_state)
            selected_entry = get_agent_by_id(selected_agent_id)
            if selected_entry is None:
                return {
                    "message": f"Unknown agent: {selected_agent_id}",
                    "state_snapshot": project_state.model_dump() if hasattr(project_state, "model_dump") else None,
                    "artifacts": [],
                    "intent": {"primary_intent": "manual", "requires_agents": [], "confidence": 0.0},
                    "plan": None,
                    "project_state": project_state,
                    "agent_results": [],
                    "available_agents": available_agents,
                }
            selected_availability = next(
                (item for item in available_agents if item.get("agent_id") == selected_agent_id),
                None,
            )
            if selected_availability and not selected_availability.get("is_available", False):
                reason_parts = []
                if not selected_availability.get("is_phase_compatible", True):
                    reason_parts.append(
                        f"not allowed in phase '{getattr(project_state, 'current_phase', 'initialization')}'"
                    )
                unmet = selected_availability.get("unmet_requires") or []
                if unmet:
                    reason_parts.append(f"missing required context: {', '.join(unmet)}")
                reason = "; ".join(reason_parts) if reason_parts else "not available right now"
                return {
                    "message": f"Agent '{selected_agent_id}' is unavailable: {reason}.",
                    "state_snapshot": project_state.model_dump() if hasattr(project_state, "model_dump") else None,
                    "artifacts": [],
                    "intent": {"primary_intent": "manual", "requires_agents": [selected_agent_id], "confidence": 1.0},
                    "plan": None,
                    "project_state": project_state,
                    "agent_results": [],
                    "available_agents": available_agents,
                }
            from src.orchestrator.execution_planner import _resolve_upstream
            resolved_ids = _resolve_upstream([selected_agent_id], project_state)
            from src.orchestrator.execution_plan import ExecutionPlan
            plan = ExecutionPlan()
            for aid in resolved_ids:
                entry = get_agent_by_id(aid)
                plan.add_task(agent_id=aid, required_context=(entry or {}).get("requires") or [])
            intent = {"primary_intent": "manual", "requires_agents": [selected_agent_id], "confidence": 1.0}
            # Persist mode selection
            project_state = await self.state.update(session_id, {"agent_selection_mode": "manual", "selected_agent_id": selected_agent_id})
            graph_result = {"plan": plan, "project_state": project_state, "intent": intent, "error": None}
        else:
            graph_result = await self._graph.ainvoke(initial)
            project_state = graph_result.get("project_state")
            available_agents = self._get_available_agents(project_state) if project_state else []
        error = graph_result.get("error")
        if error:
            return {
                "message": f"Error: {error}",
                "state_snapshot": None,
                "artifacts": [],
                "intent": None,
                "plan": graph_result.get("plan"),
                "project_state": None,
                "agent_results": [],
                "available_agents": available_agents if agent_selection_mode == "manual" else [],
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
                "agent_results": [],
                "available_agents": available_agents,
            }
        results = []
        agent_results = []
        blocked_artifacts: set[str] = set()
        for task in plan.tasks:
            if self._is_blocked_by_dependency(task.required_context, blocked_artifacts):
                entry = get_agent_by_id(task.agent_id)
                agent_results.append({
                    "agent_id": task.agent_id,
                    "agent_name": (entry or {}).get("name", task.agent_id),
                    "status": "blocked_dependency",
                    "content": "",
                    "state_delta_keys": [],
                    "blocked_by": sorted(blocked_artifacts),
                })
                continue
            agent = self.registry.get_agent(task.agent_id) if hasattr(self.registry, "get_agent") else None
            if agent is None:
                blocked_artifacts.update(self._produced_artifacts(task.agent_id))
                entry = get_agent_by_id(task.agent_id)
                agent_results.append({
                    "agent_id": task.agent_id,
                    "agent_name": (entry or {}).get("name", task.agent_id),
                    "status": "skipped_unavailable",
                    "content": "",
                    "state_delta_keys": [],
                })
                continue
            context = self._extract_context(project_state, task.required_context)
            entry = get_agent_by_id(task.agent_id)
            try:
                timeout_seconds = AGENT_TIMEOUT_SECONDS.get(task.agent_id, 120.0)
                result = await asyncio.wait_for(
                    self._run_agent(task, context, user_input or "", agent, project_state=project_state),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                blocked_artifacts.update(self._produced_artifacts(task.agent_id))
                agent_results.append({
                    "agent_id": task.agent_id,
                    "agent_name": (entry or {}).get("name", task.agent_id),
                    "status": "failed_timeout",
                    "content": "",
                    "state_delta_keys": [],
                    "error": f"Timed out after {timeout_seconds:.0f}s",
                })
                continue
            except Exception as exc:
                print(f"[orchestrator] agent '{task.agent_id}' failed: {type(exc).__name__}: {exc}", flush=True)
                blocked_artifacts.update(self._produced_artifacts(task.agent_id))
                agent_results.append({
                    "agent_id": task.agent_id,
                    "agent_name": (entry or {}).get("name", task.agent_id),
                    "status": "failed_runtime",
                    "content": "",
                    "state_delta_keys": [],
                    "error": f"{type(exc).__name__}: {exc}",
                })
                continue
            if not result:
                blocked_artifacts.update(self._produced_artifacts(task.agent_id))
                agent_results.append({
                    "agent_id": task.agent_id,
                    "agent_name": (entry or {}).get("name", task.agent_id),
                    "status": "failed_runtime",
                    "content": "",
                    "state_delta_keys": [],
                    "error": "Agent returned no result",
                })
                continue
            state_delta = result.get("state_delta") or {}
            if state_delta:
                project_state = await self.state.update(session_id, state_delta)
            # 3.2 Phase transition: update current_phase after agent completes.
            next_phase = PHASE_TRANSITION_MAP.get(task.agent_id)
            if next_phase:
                project_state = await self.state.update(session_id, {"current_phase": next_phase})
            results.append(result)
            agent_results.append({
                "agent_id": task.agent_id,
                "agent_name": (entry or {}).get("name", task.agent_id),
                "status": "success",
                "content": result.get("content") or "",
                "state_delta_keys": list(state_delta.keys()),
            })
        message = self._synthesize_response(results, agent_results)
        issue_summary = self._summarize_agent_issues(agent_results)
        if issue_summary:
            message = f"{message} Issues: {issue_summary}" if results else f"Issues: {issue_summary}"
        # 3.3 Conversation history: append user + assistant turns and persist.
        # We set the field directly (bypassing StateManager's list-extend merge)
        # so re-running process_request never double-appends old entries.
        new_history = list(project_state.conversation_history or [])
        new_history.append({"role": "user", "content": user_input or ""})
        new_history.append({"role": "assistant", "content": message})
        project_state.conversation_history = new_history
        if hasattr(self.state, "db") and hasattr(self.state.db, "save"):
            await self.state.db.save(session_id, project_state.model_dump())
        if hasattr(self.state, "cache"):
            self.state.cache[session_id] = project_state
        return {
            "message": message,
            "state_snapshot": project_state.model_dump() if project_state else None,
            "artifacts": results,
            "intent": graph_result.get("intent"),
            "plan": plan,
            "project_state": project_state,
            "agent_results": agent_results,
            "available_agents": available_agents,
        }

    def _get_available_agents(self, project_state: Any) -> list[dict]:
        """Return all agents with phase/dependency readiness metadata for the UI agent picker."""
        agents = []
        current_phase = getattr(project_state, "current_phase", "initialization")
        for entry in AGENT_STORE:
            phases = entry.get("phase_compatibility") or []
            is_phase_compatible = "*" in phases or current_phase in phases
            unmet_requires = self._unmet_requires(project_state, entry.get("requires") or [])
            blocked_by = [
                producer
                for producer in (get_producer_for_artifact(artifact) for artifact in unmet_requires)
                if producer
            ]
            agents.append({
                "agent_id": entry["id"],
                "agent_name": entry.get("name", entry["id"]),
                "description": entry.get("description", ""),
                "phase_compatibility": phases,
                "interaction_mode": entry.get("interaction_mode", "functional"),
                "supports_selective_regen": bool(entry.get("supports_selective_regen", False)),
                "expensive": bool(entry.get("expensive", False)),
                "is_phase_compatible": is_phase_compatible,
                "unmet_requires": unmet_requires,
                "blocked_by": blocked_by,
                "is_available": is_phase_compatible and not unmet_requires,
            })
        return agents

    def _state_has_artifact(self, project_state: Any, key: str) -> bool:
        if key == "*":
            return True
        val = getattr(project_state, key, None)
        if val is None:
            return False
        if isinstance(val, (list, dict)):
            return len(val) > 0
        if hasattr(val, "model_dump"):
            dumped = val.model_dump()
            if isinstance(dumped, dict):
                return any(value not in (None, "", [], {}, False) for value in dumped.values())
        return True

    def _unmet_requires(self, project_state: Any, requires: list[str]) -> list[str]:
        if "*" in requires:
            return []
        return [artifact for artifact in requires if not self._state_has_artifact(project_state, artifact)]

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

    def _to_dict(self, value: Any) -> dict:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return {}

    def _produced_artifacts(self, agent_id: str) -> list[str]:
        entry = get_agent_by_id(agent_id) or {}
        return list(entry.get("produces") or [])

    def _is_blocked_by_dependency(self, required_context: list[str], blocked_artifacts: set[str]) -> bool:
        if not blocked_artifacts:
            return False
        if "*" in (required_context or []):
            return True
        return any(key.split(".")[0] in blocked_artifacts for key in (required_context or []))

    def _summarize_agent_issues(self, agent_results: list[dict]) -> str:
        issues = []
        for ar in agent_results:
            status = ar.get("status") or ""
            if status == "success":
                continue
            agent_id = ar.get("agent_id") or "agent"
            detail = ar.get("error") or ar.get("blocked_by")
            issues.append(f"{agent_id}: {status}{f' ({detail})' if detail else ''}")
        return "; ".join(issues)

    def _requirements_to_collector_state(self, requirements: Any) -> Any:
        """Translate canonical requirements into the collector's RequirementsState."""
        from src.protocols.schemas import RequirementsState

        req = self._to_dict(requirements)
        return RequirementsState(
            project_type=req.get("project_type"),
            target_users=req.get("target_users") or [],
            key_features=req.get("functional") or [],
            technical_constraints=req.get("constraints") or [],
            business_goals=req.get("business_goals") or [],
            timeline=req.get("timeline"),
            budget=req.get("budget"),
            is_complete=bool(req.get("is_complete", False)),
            progress=float(req.get("progress", 0.0) or 0.0),
        )

    def _collector_state_to_requirements_delta(self, collector_requirements: Any, existing: Any) -> dict:
        """Merge collector output into canonical requirements without wiping unrelated fields."""
        current = self._to_dict(existing)
        if hasattr(collector_requirements, "model_dump"):
            rs_dump = collector_requirements.model_dump()
        else:
            rs_dump = self._to_dict(collector_requirements)

        merged = dict(current)
        if rs_dump.get("project_type") is not None:
            merged["project_type"] = rs_dump.get("project_type")
        if rs_dump.get("key_features") not in (None, []):
            merged["functional"] = rs_dump.get("key_features") or []
        if rs_dump.get("technical_constraints") not in (None, []):
            merged["constraints"] = rs_dump.get("technical_constraints") or []
        if rs_dump.get("target_users") not in (None, []):
            merged["target_users"] = rs_dump.get("target_users") or []
        if rs_dump.get("business_goals") not in (None, []):
            merged["business_goals"] = rs_dump.get("business_goals") or []
        if rs_dump.get("timeline") not in (None, ""):
            merged["timeline"] = rs_dump.get("timeline")
        if rs_dump.get("budget") not in (None, ""):
            merged["budget"] = rs_dump.get("budget")
        if "is_complete" in rs_dump:
            merged["is_complete"] = bool(rs_dump.get("is_complete"))
        if "progress" in rs_dump and rs_dump.get("progress") is not None:
            merged["progress"] = float(rs_dump.get("progress") or 0.0)
        return merged

    def _normalize_mockups(self, entries: list[Any]) -> list[dict]:
        normalized: list[dict] = []
        for entry in entries:
            item = self._to_dict(entry)
            if not item.get("screen_name") and item.get("screen_id"):
                item["screen_name"] = item["screen_id"]
            if "interactions" not in item or item.get("interactions") is None:
                item["interactions"] = []
            if not item.get("wireframe_code"):
                scene = item.get("excalidraw_scene")
                spec = item.get("wireframe_spec")
                if scene is not None:
                    item["wireframe_code"] = json.dumps(scene, default=str)
                elif spec is not None:
                    item["wireframe_code"] = json.dumps(spec, default=str)
            normalized.append(item)
        return normalized

    async def _run_agent(
        self,
        task: Task,
        context: dict,
        user_input: str,
        agent: Any,
        *,
        project_state: Any | None = None,
    ) -> dict | None:
        """Run agent for task; return { state_delta, content } or None."""
        agent_id = task.agent_id
        if agent_id == "project_architect":
            req = context.get("requirements")
            req_dict = req if isinstance(req, dict) else (req.model_dump() if hasattr(req, "model_dump") else {})
            input_data = {
                "requirements": req_dict,
                "existing_architecture": context.get("architecture") or self._to_dict(getattr(project_state, "architecture", None)),
                "user_request": user_input,
            }
            raw = await agent.process(input_data)
            state_delta = raw.get("state_delta") or {}
            if not state_delta and raw.get("architecture") is not None:
                state_delta = {"architecture": raw["architecture"]}
            return {"state_delta": state_delta, "content": raw.get("summary") or ""}

        if agent_id == "requirements_collector":
            req = context.get("requirements")
            rs = self._requirements_to_collector_state(req)
            history = context.get("conversation_history") or []
            raw = await agent.process_message(user_input, rs, history)
            req_out = raw.get("requirements")
            if req_out is None:
                return {"state_delta": {}, "content": raw.get("response") or ""}
            state_delta = {
                "requirements": self._collector_state_to_requirements_delta(
                    req_out,
                    getattr(project_state, "requirements", None) if project_state is not None else req,
                )
            }
            return {"state_delta": state_delta, "content": raw.get("response") or ""}

        if agent_id == "execution_planner":
            payload = {
                "requirements": context.get("requirements") or self._to_dict(getattr(project_state, "requirements", None)),
                "architecture": context.get("architecture") or self._to_dict(getattr(project_state, "architecture", None)),
                "existing_roadmap": context.get("roadmap") or self._to_dict(getattr(project_state, "roadmap", None)),
                "user_request": user_input,
            }
            raw = await agent.process(payload)
            state_delta = raw.get("state_delta") or {}
            if not state_delta and raw.get("roadmap") is not None:
                state_delta = {"roadmap": raw.get("roadmap")}
            return {
                "state_delta": state_delta,
                "content": raw.get("summary") or raw.get("content") or "",
            }

        if agent_id == "mockup_agent":
            payload = {
                "requirements": context.get("requirements") or self._to_dict(getattr(project_state, "requirements", None)),
                "architecture": context.get("architecture") or self._to_dict(getattr(project_state, "architecture", None)),
                "platform": "web",
                "user_request": user_input,
            }
            raw = await agent.process(payload)
            state_delta = raw.get("state_delta") or {}
            if isinstance(state_delta.get("mockups"), list):
                state_delta = dict(state_delta)
                state_delta["mockups"] = self._normalize_mockups(state_delta["mockups"])
            return {
                "state_delta": state_delta,
                "content": raw.get("summary") or raw.get("content") or "",
            }

        if agent_id == "exporter":
            payload = (
                project_state.model_dump()
                if project_state is not None and hasattr(project_state, "model_dump")
                else dict(context)
            )
            payload["user_request"] = user_input

            if hasattr(agent, "execute"):
                exec_out = await agent.execute(payload, context=payload, tools=[])
                raw_content = getattr(exec_out, "content", {})
                state_delta = getattr(exec_out, "state_delta", {}) or {}
                if isinstance(raw_content, dict):
                    content = raw_content.get("summary") or raw_content.get("content") or ""
                    if not state_delta:
                        state_delta = raw_content.get("state_delta") or {}
                else:
                    content = str(raw_content) if raw_content is not None else ""
                return {"state_delta": state_delta, "content": content}

            if hasattr(agent, "process"):
                raw = await agent.process(payload)
                return {
                    "state_delta": raw.get("state_delta") or {},
                    "content": raw.get("summary") or raw.get("content") or "",
                }

        return None

    def _synthesize_response(
        self, results: list[dict], agent_results: list[dict] | None = None
    ) -> str:
        """Turn agent results into one user-facing message (summarized/formatted for display)."""
        if not results:
            return "No agents ran."
        max_display_chars = 500
        use_labels = (
            agent_results is not None
            and len(agent_results) == len(results)
        )
        parts = []
        for i, r in enumerate(results):
            c = (r.get("content") or r.get("summary") or "").strip()
            if not c:
                continue
            if len(c) > max_display_chars:
                c = c[:max_display_chars].rstrip() + "\u2026"
            label = None
            if use_labels and i < len(agent_results):
                label = (agent_results[i].get("agent_name") or agent_results[i].get("agent_id") or "").strip()
            if label:
                parts.append(f"**{label}:** {c}")
            else:
                parts.append(c)
        if not parts:
            return "Done."
        if len(parts) == 1:
            return parts[0]
        return "\n\n".join(parts)
