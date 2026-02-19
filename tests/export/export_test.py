"""Integration test for ExporterAgent with contained outputs."""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# 1. Path calculations for tests/export/export_test.py
current_dir = Path(__file__).resolve().parent  # This is the 'tests/export' folder
project_root = current_dir.parent.parent       # Go up two levels to the main project root

# 2. Ensure the outputs directory exists right next to this script
outputs_dir = current_dir / "outputs"
outputs_dir.mkdir(exist_ok=True)

# 3. FORCE the working directory to be the 'tests/export' folder.
# This guarantees the Agent's "outputs/" folder maps perfectly to tests/export/outputs/
os.chdir(current_dir)

# 4. Load environment variables from .env
from dotenv import load_dotenv
env_file = project_root / ".env"
load_dotenv(env_file)

# 5. Ensure Python can find your 'src' folder
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.agents.exporter_agent import get_agent

# 6. Save the text log directly into the outputs folder
OUTPUT_FILE = outputs_dir / "export_test_output.txt"

# --- Realistic mock payload ---
MOCK_PROJECT_STATE = {
    "project_name": "FlyNext Travel App",
    "requirements": {
        "functional": [
            "User authentication via Google OAuth",
            "Search for flights by date and destination",
            "Book and pay for flights using Stripe"
        ],
        "user_stories": [
            {"role": "Traveler", "goal": "search for flights", "reason": "plan a vacation"},
            {"role": "Admin", "goal": "view booking metrics", "reason": "track revenue"}
        ]
    },
    "architecture": {
        "tech_stack": {
            "frontend": "Next.js + Tailwind CSS",
            "backend": "FastAPI (Python)",
            "database": "PostgreSQL",
            "devops": "Docker + AWS S3"
        },
        "system_diagram": "graph TD\nUser-->Frontend\nFrontend-->FastAPI\nFastAPI-->Postgres",
        "data_schema": "erDiagram\nUSER ||--o{ BOOKING : places\nUSER { string email }",
        "deployment_strategy": "Containerized via Docker, deployed to AWS ECS."
    },
    "roadmap": {
        "milestones": [
            {"name": "Phase 1: Core Backend", "target_date": "Week 1"},
            {"name": "Phase 2: Frontend & Stripe", "target_date": "Week 3"}
        ]
    },
    "mockups": [
        {"screen_name": "Landing Page", "user_flow": "User clicks 'Search Flights'"},
        {"screen_name": "Checkout", "user_flow": "User enters credit card details"}
    ]
}

class TestReport:
    """Writes structured test output to console and file."""
    def __init__(self, filepath: Path):
        self._filepath = filepath
        self._file = open(self._filepath, "w", encoding="utf-8")
        
    def write(self, text: str):
        print(text)
        self._file.write(text + "\n")
        
    def close(self):
        self._file.close()

async def run_test():
    report = TestReport(OUTPUT_FILE)
    report.write(f"{'=' * 70}")
    report.write(f"  ExporterAgent — Integration Test")
    report.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.write(f"{'=' * 70}\n")

    try:
        report.write("Initializing Exporter Agent...")
        agent = get_agent()

        report.write("Executing Agent with Mock Project State...")
        result = await agent.execute(input=MOCK_PROJECT_STATE, context={})

        report.write(f"\n{'─' * 70}")
        report.write("  TEST RESULTS")
        report.write(f"{'─' * 70}\n")

        status = result.metadata.get("status", "success")
        report.write(f"Agent Status: {status.upper()}")

        delta = result.state_delta.get("export_artifacts", {})
        report.write(f"Returned State Delta: {'YES' if delta else 'NO'}")

        markdown = delta.get("markdown_content", "")
        report.write(f"Markdown Generated: {'YES' if markdown else 'NO'} ({len(markdown)} characters)")
        
        summary = delta.get("executive_summary", "")
        report.write(f"LLM Executive Summary: {'YES' if summary else 'NO'}")

        # --- UPDATED CHECK ---
        # We now check metadata for the PDF path, since it's not in the state object
        pdf_path = result.metadata.get("saved_path", "")
        
        if pdf_path and os.path.exists(pdf_path):
            report.write(f"PDF File Created: YES -> {pdf_path}")
        else:
            report.write(f"PDF File Created: NO (Path: {pdf_path})")

        report.write("\n--- MARKDOWN SNIPPET ---")
        report.write(markdown[:500] + "\n... [TRUNCATED] ...")

    except Exception as e:
        report.write(f"\n❌ ERROR: {e}")
    finally:
        report.close()
        print(f"\n📄 Test report saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(run_test())