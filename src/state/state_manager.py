"""State manager with cache-first loading and atomic delta updates."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from src.state.project_state import ProjectState
from pydantic import BaseModel


class StateManager:
    def __init__(self, persistence_adapter: Any):
        self.db = persistence_adapter
        self.cache: Dict[str, ProjectState] = {}

    async def load(self, session_id: str) -> ProjectState:
        """Load state from cache or persistence."""
        if session_id in self.cache:
            return self.cache[session_id]

        state_dict = await self.db.get(session_id)
        state = ProjectState(**state_dict) if state_dict else ProjectState(session_id=session_id)
        self.cache[session_id] = state
        return state

    async def update(self, session_id: str, delta: dict) -> ProjectState:
        """
        Atomically apply a state delta and persist the result.
        Supports top-level keys and dotted paths.
        """
        state = await self.load(session_id)

        for key, value in delta.items():
            self._apply_delta(state, key, value)

        state.updated_at = datetime.utcnow()
        await self.db.save(session_id, state.model_dump())
        self.cache[session_id] = state
        return state

    async def get_fragment(self, session_id: str, path: str) -> Any:
        """
        Extract a specific state fragment by dotted path.
        Example: get_fragment("session_123", "architecture.tech_stack")
        """
        state = await self.load(session_id)
        keys = path.split(".")
        value: Any = state
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = getattr(value, key, None)
        return value

    def _apply_delta(self, state: ProjectState, key: str, value: Any) -> None:
        if "." not in key:
            self._merge_or_set(state, key, value)
            return

        keys = key.split(".")
        target: Any = state
        for part in keys[:-1]:
            target = target.get(part) if isinstance(target, dict) else getattr(target, part)

        leaf = keys[-1]
        if isinstance(target, dict):
            current = target.get(leaf)
            target[leaf] = self._merged_value(current, value)
            return

        current = getattr(target, leaf, None)
        setattr(target, leaf, self._merged_value(current, value))

    def _merge_or_set(self, state: ProjectState, key: str, value: Any) -> None:
        if not hasattr(state, key):
            return
        current = getattr(state, key)
        setattr(state, key, self._merged_value(current, value))

    def _merged_value(self, current: Any, value: Any) -> Any:
        if isinstance(current, BaseModel) and isinstance(value, dict):
            # Preserve pydantic model types on updates.
            return current.model_copy(update=value)
        if isinstance(current, list):
            merged = list(current)
            merged.extend(value if isinstance(value, list) else [value])
            return merged
        if isinstance(current, dict) and isinstance(value, dict):
            merged = dict(current)
            merged.update(value)
            return merged
        return value
