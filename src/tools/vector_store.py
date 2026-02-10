"""Vector store abstraction for retrieval-augmented generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import numpy as np

# Type for optional per-chunk metadata (e.g. source_url, diagram_type, section)
MetadataDict = dict[str, Any]

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
        self._metadata: list[MetadataDict | None] = []  # same length as _texts; None or {} if none
        self._index: Any = None  # faiss.IndexFlatL2 or None
        self._dimension: Optional[int] = None
        self._load_if_exists()

    def _index_path(self) -> Path:
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        return self.persist_dir / f"{self.store_name}.index"

    def _texts_path(self) -> Path:
        return self.persist_dir / f"{self.store_name}_texts.json"

    def _metadata_path(self) -> Path:
        return self.persist_dir / f"{self.store_name}_metadata.json"

    def _load_if_exists(self) -> None:
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
                return
            meta_path = self._metadata_path()
            if meta_path.is_file():
                with open(meta_path, encoding="utf-8") as f:
                    self._metadata = json.load(f)
                if len(self._metadata) != len(self._texts):
                    self._metadata = [None] * len(self._texts)
            else:
                self._metadata = [None] * len(self._texts)
        except Exception:
            self._index = None
            self._texts = []
            self._metadata = []

    def _ensure_index(self, dimension: int) -> None:
        if self._index is not None:
            return
        if faiss is None:
            raise RuntimeError("faiss-cpu is not installed. pip install faiss-cpu")
        self._dimension = dimension
        self._index = faiss.IndexFlatL2(dimension)

    def add(self, key: str, embedding: list[float], metadata: MetadataDict | None = None) -> None:
        """Add one embedding with an associated text key and optional metadata."""
        vec = np.array(embedding, dtype=np.float32)
        if vec.ndim == 1:
            vec = vec.reshape(1, -1)
        dim = vec.shape[1]
        self._ensure_index(dim)
        if dim != self._dimension:
            raise ValueError(f"Embedding dimension {dim} does not match index dimension {self._dimension}")
        self._index.add(vec)
        self._texts.append(key)
        self._metadata.append(metadata if metadata is not None else None)

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

    def add_text(self, text: str, metadata: MetadataDict | None = None) -> None:
        """Embed text with the configured embedder and add to the store (optional metadata)."""
        if self._embedder is None:
            raise RuntimeError("No embedder configured. Pass embedder=... to __init__ or use add(key, embedding).")
        emb = self._embed(text)
        self.add(text, emb, metadata=metadata)

    def query_text(self, text: str, k: int = 5) -> list[str]:
        """Embed text and return up to k most similar stored texts."""
        if self._embedder is None:
            raise RuntimeError("No embedder configured. Pass embedder=... to __init__ or use query(embedding, k).")
        emb = self._embed(text)
        return self.query(emb, k=k)

    def query_with_metadata(
        self, embedding: list[float], k: int = 5
    ) -> list[tuple[str, MetadataDict | None]]:
        """Return up to k (text, metadata) pairs most similar to the query embedding."""
        if self._index is None or not self._texts:
            return []
        vec = np.array(embedding, dtype=np.float32)
        if vec.ndim == 1:
            vec = vec.reshape(1, -1)
        k = min(k, len(self._texts))
        _, indices = self._index.search(vec, k)
        result = []
        for i in indices[0]:
            i = int(i)
            if 0 <= i < len(self._texts):
                meta = self._metadata[i] if i < len(self._metadata) else None
                result.append((self._texts[i], meta))
        return result

    def query_text_with_metadata(
        self,
        text: str,
        k: int = 5,
        meta_filter: MetadataDict | None = None,
        fetch_k: int | None = None,
    ) -> list[tuple[str, MetadataDict | None]]:
        """Embed text, retrieve (text, metadata) pairs; optionally filter by meta_filter (e.g. diagram_type)."""
        if self._embedder is None:
            raise RuntimeError("No embedder configured.")
        emb = self._embed(text)
        to_fetch = (fetch_k or max(k * 3, 20)) if meta_filter else k
        to_fetch = min(to_fetch, len(self._texts)) if self._texts else k
        pairs = self.query_with_metadata(emb, k=to_fetch)
        if not meta_filter:
            return pairs[:k]
        filtered = []
        for t, meta in pairs:
            if meta and all(meta.get(key) == val for key, val in meta_filter.items()):
                filtered.append((t, meta))
                if len(filtered) >= k:
                    break
        return filtered[:k]

    def _embed(self, text: str) -> list[float]:
        if hasattr(self._embedder, "encode"):
            out = self._embedder.encode(text)
            if hasattr(out, "tolist"):
                return out.tolist()
            return list(out)
        raise RuntimeError("Embedder must have an encode(text) method returning a vector.")

    def save(self) -> None:
        """Persist the FAISS index, text list, and metadata to disk."""
        if self._index is None:
            return
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        idx_path = self.persist_dir / f"{self.store_name}.index"
        texts_path = self.persist_dir / f"{self.store_name}_texts.json"
        faiss.write_index(self._index, str(idx_path))
        with open(texts_path, "w", encoding="utf-8") as f:
            json.dump(self._texts, f, ensure_ascii=False)
            f.flush()
        meta_path = self._metadata_path()
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, ensure_ascii=False)
            f.flush()

    def __len__(self) -> int:
        return len(self._texts)