"""Abstract base class for all agent implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Defines the shared interface and review protocol hook."""

    @abstractmethod
    def run(self, payload: dict) -> dict:
        """Execute the agent-specific task and return results."""
        raise NotImplementedError

    def review(self, output: dict) -> dict:
        """Hook for inline review and quality checks."""
        return output
