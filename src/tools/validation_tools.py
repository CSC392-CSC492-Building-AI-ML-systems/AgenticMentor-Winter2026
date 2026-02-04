"""Validation helpers for schema and payload checks."""

from __future__ import annotations


def validate_schema(payload: dict, schema: dict) -> bool:
    """Return True if payload matches schema keys (placeholder)."""
    return all(key in payload for key in schema.keys())
