"""Base agent implementation with review and retry support."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.protocols.review_protocol import ReviewProtocol, ReviewResult


@dataclass
class AgentOutput:
    """Normalized payload returned by every agent execution."""

    content: Any
    state_delta: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for specialist agents using inline review and retries."""

    def __init__(
        self,
        name: str,
        llm_client: Any = None,
        review_config: Optional[dict] = None,
    ) -> None:
        self.name = name
        self.llm = llm_client
        self.llm_client = llm_client
        self.reviewer = ReviewProtocol(review_config or {})

    async def execute(
        self,
        input: Any,
        context: Optional[dict] = None,
        tools: Optional[list] = None,
    ) -> AgentOutput:
        """
        Execute an agent with an inline review loop and correction retries.
        """
        max_attempts = 3
        attempt = 0
        context = context or {}
        tools = tools or []
        raw_output: Any = {}

        while attempt < max_attempts:
            raw_output = await self._generate(input, context, tools)
            review_result = await self.review(raw_output, context)

            if review_result.is_valid:
                return AgentOutput(
                    content=raw_output,
                    state_delta=self._extract_state_delta(raw_output),
                    metadata={
                        "agent": self.name,
                        "review_score": review_result.score,
                        "attempts": attempt + 1,
                    },
                )

            input = self._build_correction_prompt(
                original_input=input,
                failed_output=raw_output,
                review_feedback=review_result.feedback,
            )
            attempt += 1

        return AgentOutput(
            content=raw_output,
            state_delta={},
            metadata={
                "agent": self.name,
                "status": "degraded",
                "review_failures": attempt,
            },
        )

    async def review(self, artifact: Any, context: Optional[dict] = None) -> ReviewResult:
        """Default review uses shared protocol with agent-specific criteria."""
        return await self.reviewer.validate(
            output=artifact,
            context=context or {},
            quality_criteria=self._get_quality_criteria(),
        )

    def _build_correction_prompt(
        self, original_input: Any, failed_output: Any, review_feedback: list[str]
    ) -> Any:
        """Build a correction payload that can be fed to the next generation attempt."""
        if isinstance(original_input, dict):
            payload = dict(original_input)
            payload["previous_output"] = failed_output
            payload["review_feedback"] = review_feedback
            return payload

        feedback_text = "; ".join(review_feedback) if review_feedback else "Unknown issue"
        return (
            f"{original_input}\n\n"
            f"The previous output failed validation. Fix these issues: {feedback_text}"
        )

    def _extract_state_delta(self, raw_output: Any) -> Dict[str, Any]:
        """Extract state delta from an agent payload."""
        if isinstance(raw_output, dict):
            delta = raw_output.get("state_delta")
            if isinstance(delta, dict):
                return delta
        return {}

    @abstractmethod
    async def _generate(self, input: Any, context: dict, tools: list) -> Any:
        """Agent-specific generation logic."""

    @abstractmethod
    def _get_quality_criteria(self) -> dict:
        """Return weighted review criteria for the agent."""
