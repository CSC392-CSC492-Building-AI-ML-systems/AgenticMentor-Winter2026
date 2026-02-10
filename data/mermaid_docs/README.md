# Mermaid docs ingestion config

`sources.json` lists the Mermaid.js doc pages to scrape and ingest into the vector store.

**Format:** JSON array of objects:

- **`url`** (required): Full URL to scrape (e.g. `https://mermaid.js.org/syntax/flowchart.html`).
- **`diagram_type`** (optional): Label for filtering at query time (`flowchart`, `erd`, `syntax`, or any string). Defaults to `syntax` if omitted.

**Example:** Add another page (e.g. Sequence Diagram) by appending an entry:

```json
{
  "url": "https://mermaid.js.org/syntax/sequenceDiagram.html",
  "diagram_type": "sequence"
}
```

Then re-run:

```bash
python scripts/ingest_mermaid_docs.py
```