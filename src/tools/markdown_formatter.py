"""Formats markdown content consistently."""

from __future__ import annotations
import re

def format_markdown(content: str) -> str:
    """Return a cleaned and strictly formatted markdown string."""
    if not content:
        return ""

    # 1. Normalize line endings
    text = content.replace("\r\n", "\n")

    # 2. Ensure exactly one blank line before and after headers
    text = re.sub(r'\n{2,}(#+ .*?)\n', r'\n\n\1\n\n', text)

    # 3. Ensure Mermaid blocks have proper spacing so they render correctly
    text = text.replace("```mermaid", "\n```mermaid\n")
    text = text.replace("```\n", "```\n\n")

    # 4. Clean up excessive empty lines (max 2 consecutive newlines)
    text = re.sub(r'\n{3,}', r'\n\n', text)

    return text.strip() + "\n"