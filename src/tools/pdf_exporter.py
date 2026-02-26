"""Exports markdown or HTML into a styled PDF file (with HTML fallback).

Export contains raw Excalidraw JSON and Mermaid code in code blocks (no client-side
rendering). The frontend can render those from the same data when needed.
PDF: WeasyPrint first (when available); if that fails, Playwright (Chromium) prints
the HTML to PDF. Run `playwright install chromium` once if using the Playwright path.
"""

from __future__ import annotations
import logging
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

try:
    import markdown
except ImportError:
    markdown = None  # type: ignore[assignment]
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False
    logging.warning("WeasyPrint (GTK) not found. PDF export disabled; falling back to HTML.")


class PDFExporter:
    """Converts Markdown content to a styled, professional PDF. Output is raw code blocks (JSON, Mermaid)."""

    def __init__(self):
        self.css_styles = """
        @page { margin: 2cm; }
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; word-wrap: break-word; overflow-wrap: break-word; }
        h1 { color: #111; border-bottom: 2px solid #eaecef; padding-bottom: 0.3em; }
        h2 { color: #222; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; margin-top: 1.5em; }
        h3 { color: #444; margin-top: 1.2em; }
        p, li { font-size: 11pt; overflow-wrap: break-word; word-wrap: break-word; }
        code { background-color: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px; font-family: monospace; font-size: 85%; word-break: break-word; overflow-wrap: break-word; }
        pre { background-color: #f6f8fa; padding: 16px; border-radius: 3px; border: 1px solid #e1e4e8; white-space: pre-wrap; word-wrap: break-word; overflow-wrap: break-word; overflow-x: auto; }
        pre code { background-color: transparent; padding: 0; white-space: pre-wrap; word-break: break-word; overflow-wrap: break-word; }
        table { table-layout: fixed; width: 100%; overflow-wrap: break-word; }
        td, th { word-wrap: break-word; overflow-wrap: break-word; }
        """

    def export(self, content: str, destination: str) -> None:
        """Write the markdown content to a PDF destination path. Diagrams appear as raw JSON / Mermaid code."""
        os.makedirs(os.path.dirname(destination) or '.', exist_ok=True)

        if markdown is not None:
            html_body = markdown.markdown(content, extensions=['fenced_code', 'tables', 'nl2br'])
        else:
            html_body = f"<pre>{content}</pre>"

        full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Export</title>
    <style>{self.css_styles}</style>
</head>
<body>
{html_body}
</body>
</html>
"""

        pdf_ok = False
        if WEASYPRINT_AVAILABLE:
            print(f"  [PDFExporter] Generating PDF at: {destination}")
            if os.name == "nt":
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".html", delete=False, encoding="utf-8"
                    ) as tmp:
                        tmp.write(full_html)
                        tmp_path = tmp.name
                    result = subprocess.run(
                        [sys.executable, "-m", "weasyprint", tmp_path, destination],
                        env=os.environ,
                        capture_output=True,
                        timeout=120,
                    )
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    pdf_ok = result.returncode == 0 and os.path.isfile(destination)
                except (subprocess.TimeoutExpired, Exception):
                    logging.debug("PDF subprocess failed")
            if not pdf_ok and os.name != "nt":
                try:
                    HTML(string=full_html).write_pdf(
                        destination,
                        stylesheets=[CSS(string=self.css_styles)],
                    )
                    pdf_ok = True
                except Exception as e:
                    print(f"  [PDFExporter] PDF generation failed ({e}). Falling back to HTML.")
            if pdf_ok:
                print("  [PDFExporter] PDF generation successful!")
                return
            if os.name == "nt" and not pdf_ok:
                print("  [PDFExporter] PDF generation failed (subprocess exited or crashed). Falling back to HTML.")

        if not pdf_ok:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                pass
            else:
                pdf_path = os.path.abspath(destination)
                def _run_playwright_pdf(html: str, path: str) -> bool:
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        page = browser.new_page()
                        page.set_content(html, wait_until="networkidle")
                        page.wait_for_timeout(1500)
                        page.pdf(path=path, margin={"top": "1cm", "bottom": "1cm", "left": "1.5cm", "right": "1.5cm"})
                        browser.close()
                    return os.path.isfile(path)
                try:
                    print("  [PDFExporter] Trying Playwright (Chromium)...")
                    with ThreadPoolExecutor(max_workers=1) as ex:
                        fut = ex.submit(_run_playwright_pdf, full_html, pdf_path)
                        pdf_ok = fut.result(timeout=120)
                    if pdf_ok:
                        print("  [PDFExporter] PDF generation successful (Playwright)!")
                        return
                except Exception as e:
                    print(f"  [PDFExporter] Playwright failed: {e}")

        fallback_dest = destination.replace('.pdf', '.html')
        print(f"  [PDFExporter] Saving HTML fallback: {fallback_dest}")
        print("  [PDFExporter] (Open in browser and use Print -> Save as PDF if you need a PDF.)")
        if not WEASYPRINT_AVAILABLE and os.name == "nt":
            print("  [PDFExporter] On Windows, set WEASYPRINT_DLL_DIRECTORIES (and FONTCONFIG_FILE) before starting Python; see docs/PDF_EXPORT_WINDOWS.md")
        with open(fallback_dest, "w", encoding="utf-8") as f:
            f.write(full_html)
