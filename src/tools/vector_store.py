"""Vector store abstraction for retrieval-augmented generation."""

from __future__ import annotations


class VectorStore:
    """In-memory vector store placeholder."""

    def __init__(self) -> None:
        self._items: list[tuple[str, list[float]]] = []

    def add(self, key: str, embedding: list[float]) -> None:
        """Add an embedding with a key."""
        self._items.append((key, embedding))

    def query(self, embedding: list[float]) -> list[str]:
        """Return keys ordered by rough similarity (placeholder)."""
        return [key for key, _ in self._items]
