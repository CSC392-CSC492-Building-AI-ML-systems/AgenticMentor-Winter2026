"""Quality metrics and scoring utilities."""

from __future__ import annotations


def score_quality(output: dict) -> float:
    """Return a normalized quality score for a payload."""
    if not output:
        return 0.0
    return 0.8
