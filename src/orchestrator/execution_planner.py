"""Plans multi-agent execution strategies with dependency resolution."""

from __future__ import annotations

from typing import Any

from src.orchestrator.agent_store import (
    get_agent_by_id,
    get_producer_for_artifact,
    FULL_PIPELINE_AGENT_IDS,
)
from src.orchestrator.execution_plan import ExecutionPlan, Task


def _state_has_artifact(state: Any, key: str) -> bool:
    """Return True if project_state has a non-empty value for key."""
    if key == "*":
        return True
    val = getattr(state, key, None)
    if val is None:
        return False
    if isinstance(val, (list, dict)) and len(val) == 0:
        return False
    if hasattr(val, "model_dump"):
        d = val.model_dump() if callable(getattr(val, "model_dump")) else val
        if isinstance(d, dict):
            return any(d.values()) if d else False
    return True


def _resolve_upstream(agent_ids: list[str], state: Any) -> list[str]:
    """Prepend any missing upstream agents so dependencies are satisfied. No duplicates, dependency order."""
    seen: set[str] = set()
    result: list[str] = []

    def add_with_deps(aid: str) -> None:
        if aid in seen:
            return
        entry = get_agent_by_id(aid)
        if not entry:
            seen.add(aid)
            result.append(aid)
            return
        requires = entry.get("requires") or []
        if "*" in requires:
            seen.add(aid)
            result.append(aid)
            return
        for art in requires:
            if _state_has_artifact(state, art):
                continue
            producer = get_producer_for_artifact(art)
            if producer:
                add_with_deps(producer)
        seen.add(aid)
        result.append(aid)

    for aid in agent_ids:
        add_with_deps(aid)
    return result


class ExecutionPlanner:
    """Builds an ExecutionPlan from intent and project state with dependency resolution."""

    def plan(self, intent: Any, project_state: Any) -> ExecutionPlan:
        """
        Given intent (IntentResult with requires_agents) and project_state,
        return an ExecutionPlan with tasks in dependency order (upstream first).
        """
        agent_ids = list(intent.get("requires_agents") or [])
        # When intent is unknown or empty, default to full pipeline (req -> arch -> execution_planner -> mockup -> exporter).
        if not agent_ids or (intent.get("primary_intent") == "unknown"):
            agent_ids = list(FULL_PIPELINE_AGENT_IDS)

        phase = getattr(project_state, "current_phase", "initialization")
        # Optional: filter by phase (skip agents whose phase_compatibility doesn't include phase)
        resolved = _resolve_upstream(agent_ids, project_state)

        plan = ExecutionPlan()
        for aid in resolved:
            entry = get_agent_by_id(aid)
            if not entry:
                continue
            phases = entry.get("phase_compatibility") or []
            if "*" not in phases and phase not in phases:
                continue
            required_context = list(entry.get("requires") or [])
            plan.add_task(agent_id=aid, required_context=required_context)
        return plan
