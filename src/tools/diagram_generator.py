"""Generates Mermaid.js diagrams from structured specs."""

from __future__ import annotations


def generate_mermaid(diagram_spec: str) -> str:
    """Return a Mermaid.js diagram block from a spec string."""
    return f"```mermaid\n{diagram_spec}\n```"
