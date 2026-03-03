"""Chunk markdown by headers and size for RAG ingestion."""

from __future__ import annotations

import re


def chunk_markdown(text: str, max_chars: int = 700) -> list[str]:
    """Split markdown into chunks by ## headers, then by size if needed."""
    if not (text or text.strip()):
        return []
    chunks = []
    current = []
    current_len = 0
    for part in re.split(r"\n(?=## )", text.strip()):
        part = part.strip()
        if not part:
            continue
        if current_len + len(part) + 1 <= max_chars:
            current.append(part)
            current_len += len(part) + 1
        else:
            if current:
                chunks.append("\n\n".join(current))
            if len(part) > max_chars:
                for para in re.split(r"\n\n+", part):
                    if len(para) > max_chars:
                        for i in range(0, len(para), max_chars):
                            chunks.append(para[i : i + max_chars].strip())
                    elif para.strip():
                        chunks.append(para.strip())
                current = []
                current_len = 0
            else:
                current = [part]
                current_len = len(part) + 1
    if current:
        chunks.append("\n\n".join(current))
    return [c for c in chunks if c.strip()]
