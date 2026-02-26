"""Integration test for ExporterAgent with contained outputs."""

import asyncio
import io
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Windows: ensure stdout can print Unicode (e.g. emoji, box-drawing)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

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
from src.models.wireframe_spec import WireframeSpec, ScreenSpec, ComponentSpec, NavigationLink
from src.tools.excalidraw_compiler import ExcalidrawCompiler

# 6. Save the text log directly into the outputs folder
OUTPUT_FILE = outputs_dir / "export_test_output.txt"

# ---------------------------------------------------------------------------
# Mock payloads shaped like our actual agent outputs (see src.state.project_state).
# Used to verify the exporter handles Requirements Collector, Architect,
# Execution Planner, and Mockup Agent output at any stage of the flow.
# ---------------------------------------------------------------------------

# Requirements Collector output shape (Requirements model)
PAYLOAD_REQUIREMENTS_ONLY = {
    "project_name": "FlyNext Travel App",
    "requirements": {
        "functional": [
            "User authentication via Google OAuth",
            "Search for flights by date and destination",
            "Book and pay for flights using Stripe",
        ],
        "user_stories": [
            {"role": "Traveler", "goal": "search for flights", "reason": "plan a vacation"},
            {"role": "Admin", "goal": "view booking metrics", "reason": "track revenue"},
        ],
    },
}

# Project Architect output shape (ArchitectureDefinition)
PAYLOAD_WITH_ARCHITECTURE = {
    **PAYLOAD_REQUIREMENTS_ONLY,
    "architecture": {
        "tech_stack": {
            "frontend": "Next.js + Tailwind CSS",
            "backend": "FastAPI (Python)",
            "database": "PostgreSQL",
            "devops": "Docker + AWS S3",
        },
        "tech_stack_rationale": "Next.js for SSR and SEO; FastAPI for async; PostgreSQL for relational data.",
        "system_diagram": "graph TD\nUser-->Frontend\nFrontend-->FastAPI\nFastAPI-->Postgres",
        "data_schema": "erDiagram\nUSER ||--o{ BOOKING : places\nUSER { string email }",
        "api_design": [
            {"method": "GET", "path": "/api/flights", "description": "Search flights"},
            {"method": "POST", "path": "/api/bookings", "description": "Create booking"},
        ],
        "deployment_strategy": "Containerized via Docker, deployed to AWS ECS.",
    },
}

# Execution Planner output shape (Roadmap: phases, milestones, implementation_tasks, sprints, critical_path)
PAYLOAD_WITH_EXECUTION = {
    **PAYLOAD_WITH_ARCHITECTURE,
    "roadmap": {
        "phases": [
            {"name": "Infrastructure & Auth", "description": "Setup repo, Docker, and Google OAuth", "order": 1},
            {"name": "Search & Booking", "description": "Flight search API and Stripe checkout", "order": 2},
            {"name": "Admin & Deploy", "description": "Admin dashboard and AWS deployment", "order": 3},
        ],
        "milestones": [
            {"name": "Core Backend Ready", "target_date": "Week 1", "description": "Auth and API skeleton"},
            {"name": "Frontend & Stripe Live", "target_date": "Week 3", "description": "Bookable flow end-to-end"},
            {"name": "Production Deploy", "target_date": "Week 5", "description": "AWS ECS live"},
        ],
        "implementation_tasks": [
            {"id": "init-repo", "title": "Initialize repo and CI/CD", "phase_name": "Infrastructure & Auth", "milestone_name": "Core Backend Ready", "depends_on": [], "external_resources": ["GitHub Actions"]},
            {"id": "auth-oauth", "title": "Implement Google OAuth", "phase_name": "Infrastructure & Auth", "milestone_name": "Core Backend Ready", "depends_on": ["init-repo"], "external_resources": ["Google OAuth docs"]},
            {"id": "search-api", "title": "Flight search API", "phase_name": "Search & Booking", "milestone_name": "Frontend & Stripe Live", "depends_on": ["auth-oauth"], "external_resources": []},
            {"id": "stripe-checkout", "title": "Stripe checkout integration", "phase_name": "Search & Booking", "milestone_name": "Frontend & Stripe Live", "depends_on": ["search-api"], "external_resources": ["Stripe API"]},
            {"id": "admin-dashboard", "title": "Admin booking metrics", "phase_name": "Admin & Deploy", "milestone_name": "Production Deploy", "depends_on": ["stripe-checkout"], "external_resources": []},
        ],
        "sprints": [
            {"name": "Sprint 1", "goal": "Infrastructure & Auth", "tasks": ["init-repo", "auth-oauth"]},
            {"name": "Sprint 2", "goal": "Search & Booking", "tasks": ["search-api", "stripe-checkout"]},
            {"name": "Sprint 3", "goal": "Admin & Deploy", "tasks": ["admin-dashboard"]},
        ],
        "critical_path": "init-repo -> auth-oauth -> search-api -> stripe-checkout -> admin-dashboard",
    },
}

# Mockup Agent output: use ExcalidrawCompiler so wireframes match mockup agent (sketch style, layout).
def _build_mockups_with_compiler():
    compiler = ExcalidrawCompiler()
    landing_spec = WireframeSpec(
        project_name="FlyNext",
        screens=[
            ScreenSpec(
                screen_id="landing",
                screen_name="Landing Page",
                template="form",
                components=[
                    ComponentSpec(type="header", label="FlyNext"),
                    ComponentSpec(type="search_bar", label="Search"),
                    ComponentSpec(type="form", label="Search Flights", children=["From", "To", "Date"]),
                    ComponentSpec(type="button_group", label="Actions", children=["Search Flights"]),
                ],
            ),
        ],
        navigation=[],
    )
    checkout_spec = WireframeSpec(
        project_name="FlyNext",
        screens=[
            ScreenSpec(
                screen_id="checkout",
                screen_name="Checkout",
                template="form",
                components=[
                    ComponentSpec(type="header", label="Payment"),
                    ComponentSpec(type="form", label="Card details", children=["Card number", "Expiry", "CVC"]),
                    ComponentSpec(type="button_group", label="Actions", children=["Pay", "Cancel"]),
                ],
            ),
        ],
        navigation=[],
    )
    landing_json = compiler.compile(landing_spec)
    checkout_json = compiler.compile(checkout_spec)
    return [
        {
            "screen_name": "Landing Page",
            "user_flow": "User clicks 'Search Flights'",
            "wireframe_code": json.dumps(landing_json),
            "interactions": ["focus search", "click Search Flights", "navigate to results"],
        },
        {
            "screen_name": "Checkout",
            "user_flow": "User enters payment and confirms",
            "wireframe_code": json.dumps(checkout_json),
            "interactions": ["fill card", "click Pay", "redirect to confirmation"],
        },
    ]


PAYLOAD_WITH_MOCKUPS = {
    **PAYLOAD_WITH_EXECUTION,
    "mockups": _build_mockups_with_compiler(),
}

# Full pipeline output (all agents)
PAYLOAD_FULL = PAYLOAD_WITH_MOCKUPS

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


# Test cases: each uses a payload shaped like the corresponding agent(s) output.
TEST_CASES = [
    ("1_requirements_only", "Requirements Collector only", PAYLOAD_REQUIREMENTS_ONLY),
    ("2_with_architecture", "Requirements + Project Architect", PAYLOAD_WITH_ARCHITECTURE),
    ("3_with_execution", " + Execution Planner (phases, tasks, sprints, critical path)", PAYLOAD_WITH_EXECUTION),
    ("4_full", " + Mockup Agent (wireframes, interactions) = full pipeline", PAYLOAD_WITH_MOCKUPS),
]


async def run_one_case(agent, case_id: str, label: str, payload: dict, report: TestReport) -> None:
    """Run exporter for one payload and report results. Uses project_name to get a unique output file per case."""
    # Unique project name so each case writes its own HTML/PDF (e.g. flynext_1_requirements_only.html)
    safe_suffix = case_id.replace(" ", "_")
    payload = {**payload, "project_name": f"FlyNext {safe_suffix}"}
    report.write(f"\n--- Case: {label} ---")
    try:
        result = await agent.execute(input=payload, context={})
        status = result.metadata.get("status", "success")
        report.write(f"  Status: {status.upper()}")
        delta = result.state_delta.get("export_artifacts", {})
        markdown = delta.get("markdown_content", "")
        report.write(f"  Markdown: {len(markdown)} chars")
        saved_path = result.metadata.get("saved_path", "")
        if saved_path and os.path.exists(saved_path):
            report.write(f"  File: {saved_path}")
        else:
            report.write(f"  File: (see outputs/ for .html)")
    except Exception as e:
        report.write(f"  ERROR: {e}")
        raise


async def run_all_tests():
    report = TestReport(OUTPUT_FILE)
    report.write(f"{'=' * 70}")
    report.write(f"  ExporterAgent — Integration Tests (per-agent payloads)")
    report.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.write(f"{'=' * 70}")
    report.write("")
    report.write("Payloads match: Requirements Collector, Project Architect, Execution Planner, Mockup Agent.")
    report.write("")

    try:
        report.write("Initializing Exporter Agent...")
        agent = get_agent()
        report.write("")

        for case_id, label, payload in TEST_CASES:
            report.write(f"Running case: {label}")
            await run_one_case(agent, case_id, label, payload, report)

        report.write(f"\n{'─' * 70}")
        report.write("  ALL CASES PASSED")
        report.write(f"{'─' * 70}")
        report.write("")
        report.write("Output files in tests/export/outputs/: flynext_1_requirements_only.html, ...")
    except Exception as e:
        report.write(f"\nFAILED: {e}")
    finally:
        report.close()
        print(f"\nTest report saved to: {OUTPUT_FILE}")


async def run_test():
    """Single run with full payload (backward compatible)."""
    report = TestReport(OUTPUT_FILE)
    report.write(f"{'=' * 70}")
    report.write(f"  ExporterAgent — Integration Test (full payload)")
    report.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.write(f"{'=' * 70}\n")

    try:
        report.write("Initializing Exporter Agent...")
        agent = get_agent()
        report.write("Executing Agent with full mock state (all agents)...")
        result = await agent.execute(input=PAYLOAD_FULL, context={})

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
        saved_path = result.metadata.get("saved_path", "")
        if saved_path and os.path.exists(saved_path):
            report.write(f"PDF/HTML File: {saved_path}")
        else:
            report.write(f"PDF/HTML File: (check outputs/)")
        report.write("\n--- MARKDOWN SNIPPET ---")
        report.write(markdown[:500] + "\n... [TRUNCATED] ...")
    except Exception as e:
        report.write(f"\nERROR: {e}")
    finally:
        report.close()
        print(f"\nTest report saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    # Run all test cases (requirements-only, +arch, +execution, +mockups)
    asyncio.run(run_all_tests())