"""In-memory persistence adapter for project states (MVP)."""

from __future__ import annotations

import threading
from typing import Dict, Any, List, Optional

from src.state.project_state import ProjectState


class InMemoryPersistenceAdapter:
    """Simple thread-safe in-memory store with async-compatible methods.

    Stores project states as plain dicts (Pydantic model_dump output).
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._store.get(session_id)

    async def save(self, session_id: str, state_dict: Dict[str, Any]) -> None:
        with self._lock:
            # Ensure we keep a copy to avoid external mutation
            self._store[session_id] = dict(state_dict)

    async def delete(self, session_id: str) -> None:
        with self._lock:
            if session_id in self._store:
                del self._store[session_id]

    async def list_sessions(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    async def get_last_messages(self, session_id: str, n: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            state = self._store.get(session_id)
            if not state:
                return []
            history = state.get("conversation_history", [])
            return list(history[-n:])

    async def load_state(self, session_id: str) -> Optional[ProjectState]:
        """Return a `ProjectState` model instance if stored, else None."""
        with self._lock:
            state = self._store.get(session_id)
            if not state:
                return None
            # Parse into ProjectState where possible. If shapes differ, caller can handle.
            try:
                return ProjectState(**state)
            except Exception:
                return None

    async def save_project_state(self, session_id: str, state: ProjectState) -> None:
        """Save a `ProjectState` model instance."""
        await self.save(session_id, state.model_dump())

    # Convenience helpers for tests / non-async usage
    def _get_sync(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(session_id)


# Singleton instance for quick import/use in the app (MVP).
default_memory_adapter = InMemoryPersistenceAdapter()
