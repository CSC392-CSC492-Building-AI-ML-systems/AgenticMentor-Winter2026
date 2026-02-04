"""Classifies user intent for routing in the orchestrator."""

from __future__ import annotations


class IntentClassifier:
    """Lightweight intent classifier placeholder."""

    def classify(self, user_input: str) -> str:
        """Return a coarse intent label for the given input."""
        if not user_input:
            return "unknown"
        return "general_request"
