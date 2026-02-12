"""Integration tests for FAISS-backed VectorStore (add/query, persist/load, optional embedder)."""

import json
import shutil
import sys
import traceback
from pathlib import Path

import numpy as np

# Project root for imports (file is in tests/vector_store/)
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.tools.vector_store import VectorStore


def _make_embedding(seed: int, dim: int = 4) -> list[float]:
    np.random.seed(seed)
    return np.random.randn(dim).astype(np.float32).tolist()


def test_add_and_query(tmp_path: Path) -> None:
    """Add embeddings by key and query; results are ordered by similarity."""
    store = VectorStore(store_name="test", persist_dir=tmp_path)
    dim = 4
    store.add("apple", _make_embedding(1, dim))
    store.add("banana", _make_embedding(2, dim))
    store.add("cherry", _make_embedding(3, dim))

    # Query with embedding closest to seed 2
    q = _make_embedding(2, dim)
    results = store.query(q, k=2)
    assert len(results) == 2
    assert "banana" in results
    assert results[0] == "banana"


def test_query_empty_returns_empty(tmp_path: Path) -> None:
    """Query on an empty store returns empty list."""
    store = VectorStore(store_name="empty", persist_dir=tmp_path)
    assert store.query([0.1, 0.2, 0.3, 0.4], k=2) == []
    assert len(store) == 0


def test_save_and_load(tmp_path: Path) -> None:
    """After save(), a new VectorStore with same path loads and returns same query results."""
    # Start clean so leftover data from a previous run doesn't cause "got 4"
    for f in ("persist.index", "persist_texts.json", "persist_metadata.json"):
        (tmp_path / f).unlink(missing_ok=True)

    store = VectorStore(store_name="persist", persist_dir=tmp_path)
    dim = 4
    store.add("first", _make_embedding(10, dim))
    store.add("second", _make_embedding(20, dim))
    store.save()

    idx_file = tmp_path / "persist.index"
    texts_file = tmp_path / "persist_texts.json"
    assert idx_file.is_file(), "save() did not write persist.index"
    assert texts_file.is_file(), "save() did not write persist_texts.json"
    with open(texts_file, encoding="utf-8") as f:
        saved_texts = json.load(f)
    assert len(saved_texts) == 2, f"expected 2 texts in JSON, got {len(saved_texts)}"

    loaded = VectorStore(store_name="persist", persist_dir=tmp_path)
    assert len(loaded) == 2, f"loaded store had {len(loaded)} items, expected 2"
    results = loaded.query(_make_embedding(10, dim), k=1)
    assert results == ["first"]


def test_add_text_and_query_text(tmp_path: Path) -> None:
    """add_text/query_text work when embedder is provided (mock embedder)."""
    dim = 4

    class MockEmbedder:
        def encode(self, text: str):
            # Deterministic from string for testing
            h = hash(text) % (2**32)
            np.random.seed(h)
            return np.random.randn(dim).astype(np.float32)

    embedder = MockEmbedder()
    store = VectorStore(store_name="text", persist_dir=tmp_path, embedder=embedder)
    store.add_text("flowchart with nodes and edges")
    store.add_text("sequence diagram for API calls")
    store.add_text("pie chart for statistics")

    # Same text => same embedding => must be nearest (deterministic with mock)
    results = store.query_text("flowchart with nodes and edges", k=2)
    assert len(results) >= 1
    assert results[0] == "flowchart with nodes and edges"


def test_metadata_save_load_and_query_with_metadata(tmp_path: Path) -> None:
    """Add items with metadata, save, load, and retrieve with query_with_metadata / meta_filter."""
    dim = 4
    store = VectorStore(store_name="meta", persist_dir=tmp_path)
    store.add("flowchart nodes", _make_embedding(1, dim), metadata={"diagram_type": "flowchart", "source_url": "https://mermaid.js.org/syntax/flowchart.html"})
    store.add("erd entities", _make_embedding(2, dim), metadata={"diagram_type": "erd", "source_url": "https://mermaid.js.org/syntax/entityRelationshipDiagram.html"})
    store.add("flowchart edges", _make_embedding(3, dim), metadata={"diagram_type": "flowchart"})
    store.save()

    loaded = VectorStore(store_name="meta", persist_dir=tmp_path)
    pairs = loaded.query_with_metadata(_make_embedding(1, dim), k=2)
    assert len(pairs) == 2
    texts = [p[0] for p in pairs]
    metas = [p[1] for p in pairs]
    assert "flowchart nodes" in texts
    assert any(m and m.get("diagram_type") == "flowchart" for m in metas)


def test_query_text_with_metadata_filter_empty_when_no_match(tmp_path: Path) -> None:
    """query_text_with_metadata with meta_filter returns empty when no chunks match the filter."""
    dim = 4
    class MockEmbedder:
        def encode(self, text: str):
            h = hash(text) % (2**32)
            np.random.seed(h)
            return np.random.randn(dim).astype(np.float32)

    store = VectorStore(store_name="filter", persist_dir=tmp_path, embedder=MockEmbedder())
    store.add_text("only flowchart content", metadata={"diagram_type": "flowchart"})
    store.add_text("more flowchart", metadata={"diagram_type": "flowchart"})
    # Filter for erd - no chunks have diagram_type erd
    pairs = store.query_text_with_metadata("erDiagram entities", k=2, meta_filter={"diagram_type": "erd"})
    assert pairs == []


if __name__ == "__main__":
    import sys

    def _run() -> bool:
        tmp_path = project_root / "test_output" / "vector_store_test"
        tmp_path.mkdir(parents=True, exist_ok=True)
        try:
            # Use a unique subdir per test so tests don't share state
            tests = [
                ("test_add_and_query", lambda: test_add_and_query(tmp_path / "add_query")),
                ("test_query_empty_returns_empty", lambda: test_query_empty_returns_empty(tmp_path / "empty")),
                ("test_save_and_load", lambda: test_save_and_load(tmp_path / "save_load")),
                ("test_add_text_and_query_text", lambda: test_add_text_and_query_text(tmp_path / "text")),
                ("test_metadata_save_load_and_query_with_metadata", lambda: test_metadata_save_load_and_query_with_metadata(tmp_path / "meta")),
                ("test_query_text_with_metadata_filter_empty_when_no_match", lambda: test_query_text_with_metadata_filter_empty_when_no_match(tmp_path / "filter")),
            ]
            for name, run in tests:
                try:
                    run()
                    print(f"PASSED: {name}")
                except AssertionError as e:
                    print(f"FAILED: {name}")
                    if str(e):
                        print(f"  {e}")
                    traceback.print_exc()
                    return False
            return True
        finally:
            shutil.rmtree(tmp_path, ignore_errors=True)

    try:
        import pytest

        sys.exit(pytest.main([str(Path(__file__).resolve()), "-v"]))
    except ImportError:
        sys.exit(0 if _run() else 1)
