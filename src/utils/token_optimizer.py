"""Context window management helpers."""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Rough token estimation based on whitespace."""
    return max(1, len(text.split()))
