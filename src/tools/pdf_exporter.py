"""Exports markdown or HTML into a styled PDF file (with HTML fallback)."""

from __future__ import annotations
import os
import logging

# --- THE FIX IS HERE ---
# We try to import WeasyPrint. If it fails due to missing libraries (OSError)
# or missing package (ImportError), we simply disable PDF mode safely.
try:
    import markdown
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):  # <--- Catches the Windows DLL error!
    WEASYPRINT_AVAILABLE = False
    logging.warning("WeasyPrint (GTK) not found. PDF export disabled; falling back to HTML.")

class PDFExporter:
    """Converts Markdown content to a styled, professional PDF."""

    def __init__(self):
        # A clean, GitHub-style CSS stylesheet
        self.css_styles = """
        @page { margin: 2cm; }
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #111; border-bottom: 2px solid #eaecef; padding-bottom: 0.3em; }
        h2 { color: #222; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; margin-top: 1.5em; }
        h3 { color: #444; margin-top: 1.2em; }
        p, li { font-size: 11pt; }
        code { background-color: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px; font-family: monospace; font-size: 85%; }
        pre { background-color: #f6f8fa; padding: 16px; overflow: auto; border-radius: 3px; border: 1px solid #e1e4e8; }
        pre code { background-color: transparent; padding: 0; }
        """

    def export(self, content: str, destination: str) -> None:
        """Write the markdown content to a PDF destination path."""
        # Ensure the destination folder exists
        os.makedirs(os.path.dirname(destination) or '.', exist_ok=True)

        # 1. Convert Markdown to HTML (we need this for both PDF and fallback)
        # Note: If 'markdown' lib is missing, we just wrap raw text.
        if 'markdown' in globals():
            html_body = markdown.markdown(content, extensions=['fenced_code', 'tables', 'nl2br'])
        else:
            html_body = f"<pre>{content}</pre>"

        # 2. Wrap in a standard HTML document structure
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Export</title>
            <style>{self.css_styles}</style>
        </head>
        <body>
            {html_body}
        </body>
        </html>
        """

        # 3. Try to generate PDF, or fallback to HTML
        if WEASYPRINT_AVAILABLE:
            try:
                print(f"  [PDFExporter] Generating PDF at: {destination}")
                HTML(string=full_html).write_pdf(
                    destination,
                    stylesheets=[CSS(string=self.css_styles)]
                )
                print("  [PDFExporter] ✅ PDF generation successful!")
                return
            except Exception as e:
                print(f"  [PDFExporter] ⚠️ PDF generation failed ({e}). Falling back to HTML.")
        
        # --- FALLBACK MODE ---
        # If WeasyPrint is missing or fails, save as HTML instead.
        fallback_dest = destination.replace('.pdf', '.html')
        print(f"  [PDFExporter] Saving HTML fallback: {fallback_dest}")
        with open(fallback_dest, "w", encoding="utf-8") as f:
            f.write(full_html)