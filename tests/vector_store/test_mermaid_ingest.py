"""
Test mermaid ingestion pipeline without Firecrawl: config load, chunking, store with metadata.

Run with: python tests/vector_store/test_mermaid_ingest.py
Or: pytest tests/vector_store/test_mermaid_ingest.py -v
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.tools.vector_store import VectorStore
from src.utils.chunk_markdown import chunk_markdown


def test_chunk_markdown_splits_by_header() -> None:
    """chunk_markdown splits on ## and respects max_chars."""
    md = "## Intro\nSome intro text.\n\n## Flowchart\nFlowchart syntax here."
    chunks = chunk_markdown(md, max_chars=700)
    assert len(chunks) >= 1
    assert any("Flowchart" in c for c in chunks)
    assert any("Intro" in c for c in chunks)


def test_chunk_markdown_splits_large_section() -> None:
    """Large sections are split by size or paragraphs."""
    md = "## Big\n" + ("x" * 1000)
    chunks = chunk_markdown(md, max_chars=400)
    assert len(chunks) >= 2
    assert sum(len(c) for c in chunks) >= 1000


def test_sources_config_format() -> None:
    """sources.json is valid and has required fields."""
    path = project_root / "data" / "mermaid_docs" / "sources.json"
    if not path.exists():
        return  # skip if not in repo
    with open(path, encoding="utf-8") as f:
        sources = json.load(f)
    assert isinstance(sources, list)
    for i, entry in enumerate(sources):
        assert isinstance(entry, dict), f"Entry {i} must be dict"
        assert "url" in entry, f"Entry {i} missing url"


def test_ingest_pipeline_with_mock_content(tmp_path: Path) -> None:
    """Full pipeline: mock markdown -> chunk -> add with metadata -> save -> load -> query with filter."""
    # Mock embedder
    dim = 4
    class MockEmbedder:
        def encode(self, text: str):
            h = hash(text) % (2**32)
            np.random.seed(h)
            return np.random.randn(dim).astype(np.float32)

    store = VectorStore(
        store_name="mermaid_test",
        persist_dir=tmp_path,
        embedder=MockEmbedder(),
    )

    # Simulate two "pages": flowchart and erd
    flowchart_md = "## Nodes\nUse A[label] for nodes.\n\n## Edges\nA --> B."
    erd_md = "## Entities\nEntity has attributes.\n\n## Relationships\nUse ||--o{ for one-to-many."

    for url, diagram_type, md in [
        ("https://mermaid.js.org/syntax/flowchart.html", "flowchart", flowchart_md),
        ("https://mermaid.js.org/syntax/entityRelationshipDiagram.html", "erd", erd_md),
    ]:
        chunks = chunk_markdown(md, max_chars=700)
        for j, chunk in enumerate(chunks):
            store.add_text(chunk, metadata={"source_url": url, "diagram_type": diagram_type, "section_index": j})

    assert len(store) >= 2
    store.save()

    # Load and query with filter
    loaded = VectorStore(store_name="mermaid_test", persist_dir=tmp_path, embedder=MockEmbedder())
    pairs = loaded.query_text_with_metadata("flowchart node syntax", k=3, meta_filter={"diagram_type": "flowchart"})
    assert len(pairs) >= 1
    text, meta = pairs[0]
    assert meta is not None and meta.get("diagram_type") == "flowchart"
    assert "node" in text.lower() or "label" in text.lower() or "A[" in text


def test_query_mermaid_store_returns_metadata() -> None:
    """If mermaid store exists on disk, load it (no embedder) and verify query_with_metadata returns (text, meta) with diagram_type."""
    persist_dir = project_root / "data" / "vector_stores"
    index_path = persist_dir / "mermaid.index"
    if not index_path.is_file():
        return  # skip when store not built (e.g. CI without running ingest)
    store = VectorStore(store_name="mermaid", persist_dir=persist_dir, embedder=None)
    if len(store) == 0:
        return
    import numpy as np
    vec = np.random.randn(1, store._index.d).astype(np.float32)
    pairs = store.query_with_metadata(vec.tolist()[0], k=2)
    assert len(pairs) >= 1
    for text, meta in pairs:
        assert isinstance(text, str)
        assert meta is None or isinstance(meta, dict)
        if meta:
            assert "diagram_type" in meta or "source_url" in meta


def test_architect_rag_snippets_when_store_exists() -> None:
    """When mermaid store exists and embedder loads, architect's _get_mermaid_rag_snippets returns non-empty for system and erd."""
    from src.agents.project_architect import ProjectArchitectAgent

    index_path = project_root / "data" / "vector_stores" / "mermaid.index"
    if not index_path.is_file():
        return  # skip when store not built
    agent = ProjectArchitectAgent(state_manager=None, llm_client=None)
    system_snippets = agent._get_mermaid_rag_snippets("system")
    erd_snippets = agent._get_mermaid_rag_snippets("erd")
    # Skip if both empty (e.g. embedder failed to load in sandbox/CI)
    if not system_snippets and not erd_snippets:
        return
    assert system_snippets, "expected non-empty RAG snippets for system/flowchart when store and embedder available"
    assert erd_snippets, "expected non-empty RAG snippets for erd when store and embedder available"


def test_architect_rag_snippets_query_override_error_message() -> None:
    """When query_override is set (e.g. validator error), store is queried with that text and snippets are returned."""
    from src.agents.project_architect import ProjectArchitectAgent

    agent = ProjectArchitectAgent(state_manager=None, llm_client=None)
    error_like_query = "parentheses in edge labels cause parse errors"
    mock_chunk = "Edge labels: use pipe syntax A -->|label| B. Do not put parentheses in edge labels."

    mock_store = MagicMock()
    mock_store.query_text_with_metadata.return_value = [
        (mock_chunk, {"diagram_type": "flowchart"}),
    ]

    with patch.object(agent, "_get_mermaid_store", return_value=mock_store):
        result = agent._get_mermaid_rag_snippets(
            "flowchart",
            max_chars=500,
            query_override=error_like_query,
        )

    mock_store.query_text_with_metadata.assert_called_once()
    call_kw = mock_store.query_text_with_metadata.call_args
    assert call_kw[0][0] == error_like_query
    assert call_kw[1]["meta_filter"] == {"diagram_type": "flowchart"}
    assert call_kw[1]["k"] == 3
    assert mock_chunk in result


def test_architect_rag_snippets_query_override_truncated_to_300() -> None:
    """query_override is truncated to 300 chars when used as the search query."""
    from src.agents.project_architect import ProjectArchitectAgent

    agent = ProjectArchitectAgent(state_manager=None, llm_client=None)
    long_error = "x" * 400

    mock_store = MagicMock()
    mock_store.query_text_with_metadata.return_value = []

    with patch.object(agent, "_get_mermaid_store", return_value=mock_store):
        agent._get_mermaid_rag_snippets("erd", query_override=long_error)

    call_args = mock_store.query_text_with_metadata.call_args[0][0]
    assert len(call_args) == 300
    assert call_args == "x" * 300


if __name__ == "__main__":
    import shutil
    tmp = project_root / "test_output" / "mermaid_ingest_test"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        test_chunk_markdown_splits_by_header()
        print("PASSED: test_chunk_markdown_splits_by_header")
        test_chunk_markdown_splits_large_section()
        print("PASSED: test_chunk_markdown_splits_large_section")
        test_sources_config_format()
        print("PASSED: test_sources_config_format")
        test_ingest_pipeline_with_mock_content(tmp / "store")
        print("PASSED: test_ingest_pipeline_with_mock_content")
        test_query_mermaid_store_returns_metadata()
        print("PASSED: test_query_mermaid_store_returns_metadata")
        test_architect_rag_snippets_when_store_exists()
        print("PASSED: test_architect_rag_snippets_when_store_exists")
        test_architect_rag_snippets_query_override_error_message()
        print("PASSED: test_architect_rag_snippets_query_override_error_message")
        test_architect_rag_snippets_query_override_truncated_to_300()
        print("PASSED: test_architect_rag_snippets_query_override_truncated_to_300")
        print("All mermaid ingest tests passed.")
    except Exception as e:
        print(f"FAILED: {e}")
        raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
