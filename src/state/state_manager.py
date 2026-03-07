"""State manager with cache-first loading and atomic delta updates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from src.state.project_state import Mockup, ProjectState
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

        state.updated_at = datetime.now(timezone.utc)
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
        if key == "mockups" and isinstance(value, list):
            setattr(state, key, self._merge_mockups(getattr(state, key), value))
            return
        current = getattr(state, key)
        setattr(state, key, self._merged_value(current, value))

    def _merge_mockups(self, current: Any, value: list[Any]) -> list[Mockup]:
        """Merge mockups by stable identity instead of append-only list extension."""
        ordered: list[str] = []
        by_id: dict[str, dict] = {}

        def _normalize(entry: Any) -> dict:
            if isinstance(entry, dict):
                return dict(entry)
            if hasattr(entry, "model_dump"):
                return entry.model_dump()
            return {}

        for entry in current or []:
            item = _normalize(entry)
            key = item.get("screen_id") or item.get("screen_name") or f"mockup-{len(ordered)}"
            if key not in by_id:
                ordered.append(key)
            by_id[key] = item

        for entry in value or []:
            item = _normalize(entry)
            key = item.get("screen_id") or item.get("screen_name") or f"mockup-{len(ordered)}"
            if key not in by_id:
                ordered.append(key)
            by_id[key] = item

        return [Mockup(**by_id[key]) for key in ordered]

    def _merged_value(self, current: Any, value: Any) -> Any:
        if isinstance(current, BaseModel) and isinstance(value, dict):
            # Rebuild the model from merged data so nested fragments are re-validated
            # into their canonical Pydantic types instead of drifting into raw dicts/lists.
            merged = current.model_dump()
            merged.update(value)
            return current.__class__(**merged)
        if isinstance(current, list):
            merged = list(current)
            merged.extend(value if isinstance(value, list) else [value])
            return merged
        if isinstance(current, dict) and isinstance(value, dict):
            merged = dict(current)
            merged.update(value)
            return merged
        return value
