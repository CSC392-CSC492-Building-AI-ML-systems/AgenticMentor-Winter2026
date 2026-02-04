"""Plans multi-agent execution strategies."""

from __future__ import annotations


class ExecutionPlanner:
    """Creates a list of steps for downstream agents."""

    def plan(self, intent: str) -> list[str]:
        """Return a sequence of steps based on intent."""
        return ["analyze_intent", f"dispatch_for_{intent}", "compile_output"]
