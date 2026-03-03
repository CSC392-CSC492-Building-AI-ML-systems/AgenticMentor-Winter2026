"""Provides ASCII/SVG wireframe rendering utilities."""

from __future__ import annotations


def render_wireframe(description: str) -> str:
    """Return a basic ASCII wireframe from a description."""
    return f"[Wireframe]\n{description}"
