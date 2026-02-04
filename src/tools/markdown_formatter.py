"""Formats markdown content consistently."""

from __future__ import annotations


def format_markdown(content: str) -> str:
    """Return a cleaned and formatted markdown string."""
    return content.strip() + "\n"
