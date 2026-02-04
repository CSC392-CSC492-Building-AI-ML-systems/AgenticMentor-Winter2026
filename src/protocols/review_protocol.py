"""Inline validation logic for agent outputs."""

from __future__ import annotations


class ReviewProtocol:
    """Simple review protocol placeholder."""

    def review(self, output: dict) -> dict:
        """Return reviewed output and annotations."""
        return {"approved": True, "output": output}
