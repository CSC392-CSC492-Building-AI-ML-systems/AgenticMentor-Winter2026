"""
Quick check that the mermaid vector store is queryable.
Loads the store, runs a few queries (with and without diagram_type filter), prints top results.

Usage: python scripts/query_mermaid_store.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def main() -> int:
    persist_dir = PROJECT_ROOT / "data" / "vector_stores"
    index_path = persist_dir / "mermaid.index"
    if not index_path.is_file():
        print("No mermaid store found. Run: python scripts/ingest_mermaid_docs.py", file=sys.stderr)
        return 1

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("sentence-transformers required. pip install sentence-transformers", file=sys.stderr)
        return 1

    from src.tools.vector_store import VectorStore

    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    store = VectorStore(store_name="mermaid", persist_dir=persist_dir, embedder=embedder)
    n = len(store)
    print(f"Loaded mermaid store: {n} chunks.\n")

    # Query 1: flowchart, with filter
    print("--- Query: 'flowchart node labels edges' (diagram_type=flowchart), k=2 ---")
    pairs = store.query_text_with_metadata(
        "flowchart node labels edges",
        k=2,
        meta_filter={"diagram_type": "flowchart"},
    )
    for i, (text, meta) in enumerate(pairs, 1):
        print(f"  [{i}] diagram_type={meta.get('diagram_type') if meta else '?'} source={meta.get('source_url', '')[:50]}...")
        print(f"      Preview: {text[:200].replace(chr(10), ' ')}...")
    print()

    # Query 2: erd, with filter
    print("--- Query: 'erDiagram entities relationships' (diagram_type=erd), k=2 ---")
    pairs = store.query_text_with_metadata(
        "erDiagram entities relationships",
        k=2,
        meta_filter={"diagram_type": "erd"},
    )
    for i, (text, meta) in enumerate(pairs, 1):
        print(f"  [{i}] diagram_type={meta.get('diagram_type') if meta else '?'}")
        print(f"      Preview: {text[:200].replace(chr(10), ' ')}...")
    print()

    # Query 3: no filter
    print("--- Query: 'mermaid syntax' (no filter), k=1 ---")
    pairs = store.query_text_with_metadata("mermaid syntax", k=1)
    if pairs:
        text, meta = pairs[0]
        print(f"  diagram_type={meta.get('diagram_type') if meta else '?'}")
        print(f"  Preview: {text[:200].replace(chr(10), ' ')}...")

    print("\nMermaid store is queryable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
