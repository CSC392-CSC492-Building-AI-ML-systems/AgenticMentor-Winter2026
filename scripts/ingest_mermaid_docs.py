"""
Ingest Mermaid.js doc pages into the mermaid vector store via Firecrawl.

Reads URLs (and optional diagram_type) from a JSON config file, scrapes each page,
chunks the markdown, embeds with sentence-transformers, and saves to the store.

Usage:
  python scripts/ingest_mermaid_docs.py
  python scripts/ingest_mermaid_docs.py --sources data/mermaid_docs/sources.json

Requires: FIRECRAWL_API_KEY in env, firecrawl-py, sentence-transformers, faiss-cpu.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT.parent / ".env")

from src.utils.chunk_markdown import chunk_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Mermaid docs into vector store via Firecrawl.")
    parser.add_argument(
        "--sources",
        type=Path,
        default=PROJECT_ROOT / "data" / "mermaid_docs" / "sources.json",
        help="JSON file with list of {url, diagram_type} objects",
    )
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "vector_stores",
        help="Directory for vector store index and metadata",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=700,
        help="Max characters per chunk",
    )
    args = parser.parse_args()

    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        print("Error: FIRECRAWL_API_KEY not set.", file=sys.stderr)
        return 1

    if not args.sources.is_file():
        print(f"Error: sources file not found: {args.sources}", file=sys.stderr)
        return 1

    with open(args.sources, encoding="utf-8") as f:
        sources = json.load(f)
    if not isinstance(sources, list) or not sources:
        print("Error: sources.json must be a non-empty list of {url, diagram_type} objects.", file=sys.stderr)
        return 1

    try:
        from firecrawl import Firecrawl
    except ImportError:
        print("Error: firecrawl-py not installed. pip install firecrawl-py", file=sys.stderr)
        return 1

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("Error: sentence-transformers not installed. pip install sentence-transformers", file=sys.stderr)
        return 1

    from src.tools.vector_store import VectorStore

    firecrawl = Firecrawl(api_key=api_key)
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    store = VectorStore(
        store_name="mermaid",
        persist_dir=args.persist_dir,
        embedder=embedder,
    )

    total_chunks = 0
    for i, entry in enumerate(sources):
        url = entry.get("url") if isinstance(entry, dict) else None
        diagram_type = entry.get("diagram_type", "syntax") if isinstance(entry, dict) else "syntax"
        if not url:
            print(f"Skip entry {i}: missing url")
            continue
        print(f"Scraping [{i+1}/{len(sources)}] {url} ...", flush=True)
        try:
            result = firecrawl.scrape(url, formats=["markdown"])
        except Exception as e:
            print(f"  Firecrawl error: {e}", file=sys.stderr)
            continue
        # Support both { "markdown": "..." } and { "data": { "markdown": "..." } }
        if isinstance(result, dict):
            markdown = result.get("markdown") or (result.get("data") or {}).get("markdown")
        else:
            markdown = getattr(result, "markdown", None) or getattr(getattr(result, "data", None), "markdown", None)
        markdown = markdown or ""
        if not isinstance(markdown, str) or not markdown.strip():
            print(f"  No markdown in response.")
            continue
        chunks = chunk_markdown(markdown, max_chars=args.max_chars)
        meta_base = {"source_url": url, "diagram_type": diagram_type}
        for j, chunk in enumerate(chunks):
            store.add_text(chunk, metadata={**meta_base, "section_index": j})
            total_chunks += 1
        print(f"  Chunks: {len(chunks)}")

    if total_chunks == 0:
        print("No chunks ingested.", file=sys.stderr)
        return 1
    store.save()
    print(f"Saved {total_chunks} chunks to {args.persist_dir} (store: mermaid).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
