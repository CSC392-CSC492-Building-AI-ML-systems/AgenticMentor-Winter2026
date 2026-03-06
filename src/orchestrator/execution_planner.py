"""Orchestrator routing: which agents to run next (Task/ExecutionPlan).

Note: The Execution Planner *Agent* (src.agents.execution_planner_agent) produces
the project execution plan deliverable (phases, milestones, tasks, dependencies)
for Reviewer and Exporter; it consumes Architect output.
"""
from __future__ import annotations

from typing import Any

from src.orchestrator.agent_store import (
    AGENT_STORE,
    get_agent_by_id,
    get_producer_for_artifact,
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


def _resolve_downstream(resolved_ids: list[str], state: Any) -> list[str]:
    """
    Given a list of agent ids already in the plan, find all agents that
    *require* any artifact *produced* by those agents and append them in
    topological order (no duplicates, dependency order preserved).

    Repeats until stable so chains like:
        project_architect → execution_planner → exporter
    are fully expanded.
    """
    seen: set[str] = set(resolved_ids)
    result: list[str] = list(resolved_ids)

    changed = True
    while changed:
        changed = False
        # Collect all artifacts produced by agents currently in the plan.
        produced: set[str] = set()
        for aid in result:
            entry = get_agent_by_id(aid)
            if entry:
                for art in entry.get("produces") or []:
                    produced.add(art)

        # Find agents that require any of those artifacts and aren't in plan yet.
        for entry in AGENT_STORE:
            aid = entry["id"]
            if aid in seen:
                continue
            requires = entry.get("requires") or []
            if "*" in requires:
                # exporter requires everything — only add if ALL artifacts present
                # (handled separately; skip auto-downstream for wildcard requires)
                continue
            if any(art in produced for art in requires):
                # Prepend any upstream deps this new agent itself needs.
                new_ids = _resolve_upstream([aid], state)
                for nid in new_ids:
                    if nid not in seen:
                        seen.add(nid)
                        result.append(nid)
                        changed = True

    return result


class ExecutionPlanner:
    """Builds an ExecutionPlan from intent and project state with dependency resolution."""

    def plan(self, intent: Any, project_state: Any) -> ExecutionPlan:
        """
        Given intent (IntentResult with requires_agents) and project_state,
        return an ExecutionPlan with tasks in dependency order (upstream first).
        """
        primary_intent = intent.get("primary_intent") or "unknown"
        agent_ids = list(intent.get("requires_agents") or [])
        # Unknown/empty intent should be cheap and conversational: route only to requirements collection,
        # not the full pipeline. This avoids expensive accidental fan-out on ambiguous turns.
        if not agent_ids or primary_intent == "unknown":
            agent_ids = ["requirements_collector"]

        phase = getattr(project_state, "current_phase", "initialization")
        # Resolve upstream deps first. Only expand downstream for non-conversational paths.
        resolved = _resolve_upstream(agent_ids, project_state)
        if primary_intent not in {"unknown", "requirements_gathering"}:
            resolved = _resolve_downstream(resolved, project_state)

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
