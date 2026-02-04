"""Main routing logic for delegating tasks across agents."""

from __future__ import annotations

from src.orchestrator.intent_classifier import IntentClassifier
from src.orchestrator.execution_planner import ExecutionPlanner


class MasterAgent:
    """Coordinates intent classification and execution planning."""

    def __init__(self) -> None:
        self.classifier = IntentClassifier()
        self.planner = ExecutionPlanner()

    def route(self, user_input: str) -> list[str]:
        """Classify user intent and produce a high-level plan."""
        intent = self.classifier.classify(user_input)
        return self.planner.plan(intent)
