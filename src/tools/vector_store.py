"""Vector store abstraction for retrieval-augmented generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import numpy as np

try:
    import faiss
except ImportError:
    faiss = None  # type: ignore[assignment]


class VectorStore:
    """
    FAISS-backed vector store with optional persistence and text embedding.
    One store per store_name (separate index + metadata files).
    """

    def __init__(
        self,
        store_name: str = "default",
        persist_dir: str | Path = "data/vector_stores",
        embedder: Any = None,
    ) -> None:
        self.store_name = store_name
        self.persist_dir = Path(persist_dir)
        self._embedder = embedder
        self._texts: list[str] = []
        self._index: Any = None  # faiss.IndexFlatL2 or None
        self._dimension: Optional[int] = None
        self._load_if_exists()

    def _index_path(self) -> Path:
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        return self.persist_dir / f"{self.store_name}.index"

    def _texts_path(self) -> Path:
        return self.persist_dir / f"{self.store_name}_texts.json"

    def _load_if_exists(self) -> None:
        # Check existence without creating the directory (unlike _index_path())
        idx_path = self.persist_dir / f"{self.store_name}.index"
        texts_path = self.persist_dir / f"{self.store_name}_texts.json"
        if faiss is None or not idx_path.is_file() or not texts_path.is_file():
            return
        try:
            self._index = faiss.read_index(str(idx_path))
            self._dimension = self._index.d
            with open(texts_path, encoding="utf-8") as f:
                self._texts = json.load(f)
            if len(self._texts) != self._index.ntotal:
                self._index = None
                self._texts = []
        except Exception:
            self._index = None
            self._texts = []

    def _ensure_index(self, dimension: int) -> None:
        if self._index is not None:
            return
        if faiss is None:
            raise RuntimeError("faiss-cpu is not installed. pip install faiss-cpu")
        self._dimension = dimension
        self._index = faiss.IndexFlatL2(dimension)

    def add(self, key: str, embedding: list[float]) -> None:
        """Add one embedding with an associated text key (returned by query)."""
        vec = np.array(embedding, dtype=np.float32)
        if vec.ndim == 1:
            vec = vec.reshape(1, -1)
        dim = vec.shape[1]
        self._ensure_index(dim)
        if dim != self._dimension:
            raise ValueError(f"Embedding dimension {dim} does not match index dimension {self._dimension}")
        self._index.add(vec)
        self._texts.append(key)

    def query(self, embedding: list[float], k: int = 5) -> list[str]:
        """Return up to k text keys most similar to the query embedding."""
        if self._index is None or not self._texts:
            return []
        vec = np.array(embedding, dtype=np.float32)
        if vec.ndim == 1:
            vec = vec.reshape(1, -1)
        k = min(k, len(self._texts))
        distances, indices = self._index.search(vec, k)
        return [self._texts[int(i)] for i in indices[0] if 0 <= int(i) < len(self._texts)]

    def add_text(self, text: str) -> None:
        """Embed text with the configured embedder and add to the store."""
        if self._embedder is None:
            raise RuntimeError("No embedder configured. Pass embedder=... to __init__ or use add(key, embedding).")
        emb = self._embed(text)
        self.add(text, emb)

    def query_text(self, text: str, k: int = 5) -> list[str]:
        """Embed text and return up to k most similar stored texts."""
        if self._embedder is None:
            raise RuntimeError("No embedder configured. Pass embedder=... to __init__ or use query(embedding, k).")
        emb = self._embed(text)
        return self.query(emb, k=k)

    def _embed(self, text: str) -> list[float]:
        if hasattr(self._embedder, "encode"):
            out = self._embedder.encode(text)
            if hasattr(out, "tolist"):
                return out.tolist()
            return list(out)
        raise RuntimeError("Embedder must have an encode(text) method returning a vector.")

    def save(self) -> None:
        """Persist the FAISS index and text list to disk."""
        if self._index is None:
            return
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        idx_path = self.persist_dir / f"{self.store_name}.index"
        texts_path = self.persist_dir / f"{self.store_name}_texts.json"
        faiss.write_index(self._index, str(idx_path))
        with open(texts_path, "w", encoding="utf-8") as f:
            json.dump(self._texts, f, ensure_ascii=False)
            f.flush()

    def __len__(self) -> int:
        return len(self._texts)
