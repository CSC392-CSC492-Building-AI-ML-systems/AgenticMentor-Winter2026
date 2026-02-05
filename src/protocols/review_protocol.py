"""Review protocol and validators used by specialist agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ValidationResult:
    """Result for a single validation dimension."""

    score: float
    issues: List[str] = field(default_factory=list)


@dataclass
class ReviewResult:
    """Aggregate review result for an agent artifact."""

    is_valid: bool
    score: float
    feedback: List[str] = field(default_factory=list)
    detailed_scores: Dict[str, float] = field(default_factory=dict)


class FeasibilityValidator:
    name = "feasibility"

    def check(self, output: Any, context: dict, criteria: dict) -> ValidationResult:
        issues: List[str] = []
        if output is None:
            issues.append("Output is missing")
        elif isinstance(output, str) and not output.strip():
            issues.append("Output text is empty")
        elif isinstance(output, (dict, list, tuple, set)) and len(output) == 0:
            issues.append("Output payload is empty")

        score = max(0.0, 1.0 - (0.2 * len(issues)))
        return ValidationResult(score=score, issues=issues)


class ClarityValidator:
    name = "clarity"

    def check(self, output: Any, context: dict, criteria: dict) -> ValidationResult:
        issues: List[str] = []
        if isinstance(output, str) and not output.strip():
            issues.append("Output text is blank")
        if isinstance(output, dict) and not output:
            issues.append("Output object has no keys")

        score = max(0.0, 1.0 - (0.2 * len(issues)))
        return ValidationResult(score=score, issues=issues)


class CompletenessValidator:
    name = "completeness"

    def check(self, output: Any, context: dict, criteria: dict) -> ValidationResult:
        issues: List[str] = []
        if isinstance(output, dict):
            if "state_delta" in output and output.get("state_delta") is None:
                issues.append("state_delta cannot be None")
            if "metadata" in output and output.get("metadata") is None:
                issues.append("metadata cannot be None")

        score = max(0.0, 1.0 - (0.2 * len(issues)))
        return ValidationResult(score=score, issues=issues)


class ConsistencyValidator:
    name = "consistency"

    def check(self, output: Any, context: dict, criteria: dict) -> ValidationResult:
        return ValidationResult(score=1.0, issues=[])


class ReviewProtocol:
    """Multi-dimensional validation protocol."""

    def __init__(self, config: dict):
        self.validators = [
            FeasibilityValidator(),
            ClarityValidator(),
            CompletenessValidator(),
            ConsistencyValidator(),
        ]
        self.min_score = config.get("min_score", 0.75)

    async def validate(self, output: Any, context: dict, quality_criteria: dict) -> ReviewResult:
        scores: Dict[str, float] = {}
        feedback: List[str] = []

        for validator in self.validators:
            result = validator.check(output, context, quality_criteria)
            scores[validator.name] = result.score
            feedback.extend(result.issues)

        total_score = self._calculate_weighted_score(scores, quality_criteria)
        return ReviewResult(
            is_valid=(total_score >= self.min_score and not feedback),
            score=total_score,
            feedback=feedback,
            detailed_scores=scores,
        )

    def _calculate_weighted_score(self, scores: Dict[str, float], quality_criteria: dict) -> float:
        if not scores:
            return 0.0

        default_weight = 1.0 / max(1, len(scores))
        weighted_total = 0.0
        total_weight = 0.0

        for dimension, score in scores.items():
            weight = float(quality_criteria.get(dimension, default_weight))
            weighted_total += score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0
        return weighted_total / total_weight
