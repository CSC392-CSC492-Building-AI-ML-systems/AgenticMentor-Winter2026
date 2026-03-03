"""Unit tests for PDFExporter. Export outputs raw JSON and Mermaid code blocks (no client-side rendering)."""

from __future__ import annotations

import os
import tempfile

import pytest

from src.tools.pdf_exporter import PDFExporter


def test_export_html_fallback_contains_raw_code(tmp_path):
    """Export markdown with Excalidraw JSON; PDF or HTML fallback should exist; if HTML, it has raw code."""
    pytest.importorskip("markdown")
    markdown_content = """# Plan
## Mockup
Wireframe:
```json
{"type": "excalidraw", "version": 2, "elements": [], "appState": {}}
```
"""
    dest = os.path.join(tmp_path, "out.pdf")
    PDFExporter().export(markdown_content, dest)
    pdf_path = dest
    html_path = os.path.join(tmp_path, "out.html")
    assert os.path.isfile(pdf_path) or os.path.isfile(html_path), "Either PDF or HTML fallback must be written"
    if os.path.isfile(pdf_path):
        assert os.path.getsize(pdf_path) > 0, "PDF should be non-empty"
    if os.path.isfile(html_path):
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        assert "language-json" in html or "<code>" in html
        assert "excalidraw" in html or "elements" in html
        assert "Plan" in html and "Mockup" in html


def test_export_mermaid_as_raw_code(tmp_path):
    """Export markdown with Mermaid; PDF or HTML should exist; if HTML, it has raw Mermaid code."""
    pytest.importorskip("markdown")
    markdown_content = """# Arch
## Diagram
```mermaid
graph TD
  A --> B
```
"""
    dest = os.path.join(tmp_path, "out.pdf")
    PDFExporter().export(markdown_content, dest)
    pdf_path = dest
    html_path = os.path.join(tmp_path, "out.html")
    assert os.path.isfile(pdf_path) or os.path.isfile(html_path)
    if os.path.isfile(pdf_path):
        assert os.path.getsize(pdf_path) > 0, "PDF should be non-empty"
    if os.path.isfile(html_path):
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        assert "language-mermaid" in html or "mermaid" in html
        assert "graph TD" in html
        assert "A --> B" in html
