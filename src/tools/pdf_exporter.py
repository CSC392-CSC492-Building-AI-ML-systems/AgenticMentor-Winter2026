"""Exports markdown or HTML into a PDF file."""

from __future__ import annotations


class PDFExporter:
    """Placeholder PDF export implementation."""

    def export(self, content: str, destination: str) -> None:
        """Write the content to a destination path (placeholder)."""
        with open(destination, "w", encoding="utf-8") as handle:
            handle.write(content)
