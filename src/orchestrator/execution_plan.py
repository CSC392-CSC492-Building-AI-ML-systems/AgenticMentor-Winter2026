"""Execution plan model: Task and ExecutionPlan for orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    """Single agent task in an execution plan."""
    agent_id: str
    required_context: list[str]
    input: Any = None
    tools: list[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    """Ordered list of tasks (agents to run with required context)."""
    tasks: list[Task] = field(default_factory=list)

    def add_task(
        self,
        agent_id: str,
        required_context: list[str],
        input: Any = None,
        tools: list[str] | None = None,
    ) -> None:
        self.tasks.append(
            Task(
                agent_id=agent_id,
                required_context=required_context or [],
                input=input,
                tools=tools or [],
            )
        )
