"""Orchestrator routing: which agents to run next (Task/ExecutionPlan).

Note: The Execution Planner *Agent* (src.agents.execution_planner_agent) produces
the project execution plan deliverable (phases, milestones, tasks, dependencies)
for Reviewer and Exporter; it consumes Architect output."""
from __future__ import annotations


class ExecutionPlanner:
    """Creates a list of steps for downstream agents."""

    def plan(self, intent: str) -> list[str]:
        """Return a sequence of steps based on intent."""
        return ["analyze_intent", f"dispatch_for_{intent}", "compile_output"]
