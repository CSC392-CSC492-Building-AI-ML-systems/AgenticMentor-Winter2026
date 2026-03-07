"""Persistence adapter shim. Default uses the in-memory adapter for MVP."""

from __future__ import annotations

from typing import Any

from src.storage.memory_store import default_memory_adapter


def get_default_adapter() -> Any:
    """Return the default persistence adapter instance.

    The returned adapter implements async `get(session_id)` and
    `save(session_id, state_dict)` methods as used by `StateManager`.
    """
    return default_memory_adapter
