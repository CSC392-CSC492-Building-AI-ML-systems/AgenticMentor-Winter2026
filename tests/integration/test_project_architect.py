"""Integration test for ProjectArchitectAgent with live Gemini API."""

import asyncio
import json
import sys
from datetime import datetime
from datetime import datetime
from pathlib import Path

# Load environment variables from .env (checks project root and parent)
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parents[2]
env_file = project_root / ".env"
if not env_file.exists():
    # Fall back to parent directory (where user's .env might be)
    env_file = project_root.parent / ".env"
load_dotenv(env_file)

# Ensure src.* imports work (add project root, not src subfolder)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.adapters.llm_clients import GeminiClient
from src.agents.project_architect import ProjectArchitectAgent

# Output file for structured test results
OUTPUT_FILE = Path(__file__).resolve().parent / "test_output.txt"

# Simple scenario used by the base integration test
SIMPLE_REQUIREMENTS = {
    "requirements": {
        "functional": [
            "User authentication with email and password",
            "Dashboard showing user activity",
            "REST API for mobile clients",
        ],
        "non_functional": [
            "Must handle 500 concurrent users",
            "Response time under 200ms for API calls",
        ],
        "constraints": [
            "Must use Python for backend",
        ],
    }
}

# Complex scenario from friend's test case
COMPLEX_REQUIREMENTS = {
    "requirements": {
        "functional": [
            "Multi-tenant B2B SaaS: each organization has isolated data and config",
            "SSO via SAML/OIDC; optional email/password fallback per tenant",
            "Role-based access: org admin, project manager, developer, viewer",
            "Project management: projects, milestones, tasks, file attachments",
            "Audit log: who did what and when, exportable for compliance",
            "REST and GraphQL APIs; webhooks for external integrations",
            "Real-time notifications (in-app and optional email) for assignments and deadlines",
        ],
        "non_functional": [
            "Target 10k concurrent users; 99.9% uptime SLA",
            "P95 API latency < 150ms; bulk exports may run async",
            "EU and US data residency options; encryption at rest and in transit",
            "Must run on Kubernetes; support horizontal scaling of API and workers",
        ],
        "constraints": [
            "Backend must be Python or Node.js",
            "Prefer managed services for DB and queues where possible",
        ],
        "user_stories": [
            {
                "role": "Org Admin",
                "goal": "Configure SSO and manage org members",
                "reason": "Security and onboarding",
            },
            {
                "role": "Project Manager",
                "goal": "Create projects and assign tasks with due dates",
                "reason": "Planning",
            },
        ],
    }
}

# Run mode:
# - simple: run main() + selective regeneration test
# - complex: run complex scenario only
# - both: run all tests (default)
RUN_MODE = (sys.argv[1] if len(sys.argv) > 1 else "both").lower()
if RUN_MODE not in ("simple", "complex", "both"):
    RUN_MODE = "both"


# ============================================================================
# Test Report Writer
# ============================================================================

class TestReport:
    """Writes structured test output to both console and a text file."""

    def __init__(self, filepath: Path):
        self._filepath = filepath
        self._file = None
        self._results: list[dict] = []

    def open(self):
        self._file = open(self._filepath, "w", encoding="utf-8")
        header = (
            f"{'=' * 70}\n"
            f"  ProjectArchitectAgent — Integration Test Report\n"
            f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"  Run mode:  {RUN_MODE}\n"
            f"{'=' * 70}\n"
        )
        self._write(header)

    def close(self):
        # Write summary section
        self._write(f"\n{'=' * 70}")
        self._write("  SUMMARY")
        self._write(f"{'=' * 70}\n")
        for r in self._results:
            status = "PASS" if r["passed"] else "FAIL"
            self._write(f"  [{status}] {r['name']}")
            if r.get("details"):
                for line in r["details"]:
                    self._write(f"         {line}")
        passed = sum(1 for r in self._results if r["passed"])
        total = len(self._results)
        self._write(f"\n  Result: {passed}/{total} tests passed.\n")
        if self._file:
            self._file.close()
            self._file = None

    def section(self, title: str):
        """Write a section header."""
        self._write(f"\n{'─' * 70}")
        self._write(f"  {title}")
        self._write(f"{'─' * 70}\n")

    def line(self, text: str = ""):
        """Write a line to both console and file."""
        self._write(text)

    def kv(self, key: str, value: str):
        """Write a key-value pair."""
        self._write(f"  {key}: {value}")

    def block(self, label: str, content: str):
        """Write a labeled multi-line block (e.g. a full diagram)."""
        self._write(f"\n  ── {label} ──")
        for ln in (content or "(empty)").splitlines():
            self._write(f"  {ln}")
        self._write("")

    def record_result(self, name: str, passed: bool, details: list[str] | None = None):
        """Record a test result for the summary."""
        self._results.append({"name": name, "passed": passed, "details": details or []})

    def _write(self, text: str):
        print(text)
        if self._file:
            self._file.write(text + "\n")


report = TestReport(OUTPUT_FILE)


# ============================================================================
# Mock
# ============================================================================

class MockPersistenceAdapter:
    """In-memory mock for StateManager's persistence layer."""

    def __init__(self):
        self._store: dict = {}

    async def get(self, session_id: str) -> dict | None:
        return self._store.get(session_id)

    async def save(self, session_id: str, data: dict) -> None:
        self._store[session_id] = data


def _make_agent():
    """Create agent + state manager for a test."""
    from src.state.state_manager import StateManager

    llm = GeminiClient(model="gemini-2.5-flash")
    persistence = MockPersistenceAdapter()
    state_manager = StateManager(persistence_adapter=persistence)
    return ProjectArchitectAgent(state_manager=state_manager, llm_client=llm)


def _write_architecture(arch: dict):
    """Dump full architecture output to the report."""
    ts = arch.get("tech_stack", {})
    report.kv("Frontend", ts.get("frontend", "N/A"))
    report.kv("Backend", ts.get("backend", "N/A"))
    report.kv("Database", ts.get("database", "N/A"))
    report.kv("DevOps", ts.get("devops", "N/A"))

    rationale = arch.get("tech_stack_rationale")
    if rationale:
        report.block("Tech Stack Rationale", rationale)

    if arch.get("system_diagram"):
        report.block("System Diagram (Mermaid)", arch["system_diagram"])
    else:
        report.kv("System Diagram", "MISSING")

    if arch.get("data_schema"):
        report.block("ERD Diagram (Mermaid)", arch["data_schema"])
    else:
        report.kv("ERD Diagram", "MISSING")

    report.kv("Deployment", arch.get("deployment_strategy", "N/A"))


# ============================================================================
# Tests
# ============================================================================

async def main():
    report.section("TEST 1: Simple Requirements — Full Generation")

    req = SIMPLE_REQUIREMENTS["requirements"]
    report.kv("Functional requirements", str(len(req["functional"])))
    report.kv("Non-functional requirements", str(len(req["non_functional"])))
    report.kv("Constraints", str(len(req["constraints"])))
    report.line()

    agent = _make_agent()

    try:
        result = await agent.process(SIMPLE_REQUIREMENTS)
        arch = result.get("state_delta", {}).get("architecture", result.get("architecture", {}))

        _write_architecture(arch)

        has_stack = bool(arch.get("tech_stack"))
        has_sys = bool(arch.get("system_diagram"))
        has_erd = bool(arch.get("data_schema"))
        passed = has_stack and has_sys and has_erd

        report.record_result(
            "Simple Requirements — Full Generation",
            passed,
            [
                f"tech_stack: {'OK' if has_stack else 'MISSING'}",
                f"system_diagram: {'OK' if has_sys else 'MISSING'}",
                f"data_schema: {'OK' if has_erd else 'MISSING'}",
            ],
        )
        return result

    except Exception as e:
        report.line(f"\n  ERROR: {type(e).__name__}: {e}")
        report.record_result("Simple Requirements — Full Generation", False, [str(e)])
        raise


async def test_selective_regeneration():
    report.section("TEST 2: Selective Regeneration")

    agent = _make_agent()

    # ── Step 1: Full generation ──────────────────────────────────────────
    report.line("  Step 1: Full generation (baseline)")
    test_input = {
        "requirements": {
            "functional": ["User login", "Dashboard", "REST API"],
            "constraints": ["Must use Python for backend"],
        }
    }

    result1 = await agent.process(test_input)
    arch1 = result1["architecture"]

    report.kv("Backend", arch1.get("tech_stack", {}).get("backend", "N/A"))
    report.kv("System Diagram", "generated" if arch1.get("system_diagram") else "MISSING")
    report.kv("ERD", "generated" if arch1.get("data_schema") else "MISSING")

    report.line("\n  Waiting 1 minute for API rate limits...")
    await asyncio.sleep(60)

    # ── Step 2: ERD only ─────────────────────────────────────────────────
    report.line("\n  Step 2: Selective regeneration — ERD only")
    report.kv("User request", '"Please regenerate only the ERD diagram"')

    result2 = await agent.process({
        "requirements": test_input["requirements"],
        "existing_architecture": arch1,
        "user_request": "Please regenerate only the ERD diagram",
    })
    arch2 = result2["architecture"]

    ts_preserved = arch2.get("tech_stack") == arch1.get("tech_stack")
    sys_preserved = arch2.get("system_diagram") == arch1.get("system_diagram")
    erd_changed = arch2.get("data_schema") != arch1.get("data_schema")

    report.kv("Tech Stack preserved", "YES" if ts_preserved else "NO")
    report.kv("System Diagram preserved", "YES" if sys_preserved else "NO")
    report.kv("ERD regenerated", "YES" if erd_changed else "NO")

    step2_pass = ts_preserved and sys_preserved and erd_changed
    report.record_result(
        "Selective Regen — ERD Only",
        step2_pass,
        [
            f"tech_stack preserved: {ts_preserved}",
            f"system_diagram preserved: {sys_preserved}",
            f"erd regenerated: {erd_changed}",
        ],
    )

    # ── Step 3: Backend change ───────────────────────────────────────────
    report.line("\n  Step 3: Selective regeneration — backend change")
    report.kv("User request", '"Change the backend to Node.js with Express"')

    result3 = await agent.process({
        "requirements": test_input["requirements"],
        "existing_architecture": arch1,
        "user_request": "Change the backend to Node.js with Express",
    })
    arch3 = result3["architecture"]

    ts_changed = arch3.get("tech_stack") != arch1.get("tech_stack")
    new_backend = arch3.get("tech_stack", {}).get("backend", "N/A")

    report.kv("Tech Stack changed", "YES" if ts_changed else "NO")
    report.kv("New backend", new_backend)

    _write_architecture(arch3)

    step3_pass = ts_changed
    report.record_result(
        "Selective Regen — Backend Change",
        step3_pass,
        [f"tech_stack changed: {ts_changed}", f"new backend: {new_backend}"],
    )


async def test_complex_requirements_case():
    report.section("TEST 3: Complex Requirements (B2B SaaS)")

    req = COMPLEX_REQUIREMENTS["requirements"]
    report.kv("Functional requirements", str(len(req.get("functional", []))))
    report.kv("Non-functional requirements", str(len(req.get("non_functional", []))))
    report.kv("Constraints", str(len(req.get("constraints", []))))
    report.kv("User stories", str(len(req.get("user_stories", []))))
    report.line()

    agent = _make_agent()
    result = await agent.process(COMPLEX_REQUIREMENTS)
    arch = result.get("architecture", {})

    _write_architecture(arch)

    has_stack = bool(arch.get("tech_stack"))
    has_sys = bool(arch.get("system_diagram"))
    has_erd = bool(arch.get("data_schema"))
    passed = has_stack and has_sys and has_erd

    report.record_result(
        "Complex Requirements — Full Generation",
        passed,
        [
            f"tech_stack: {'OK' if has_stack else 'MISSING'}",
            f"system_diagram: {'OK' if has_sys else 'MISSING'}",
            f"data_schema: {'OK' if has_erd else 'MISSING'}",
        ],
    )


# ============================================================================
# Runner
# ============================================================================

async def run_all_tests():
    report.open()
    report.line(f"  Run mode: {RUN_MODE}\n")

    try:
        if RUN_MODE == "simple":
            await main()
            report.line("\n  Waiting 1 minute between tests...")
            await asyncio.sleep(60)
            await test_selective_regeneration()
        elif RUN_MODE == "complex":
            await test_complex_requirements_case()
        else:
            await main()
            report.line("\n  Waiting 1 minute between tests...")
            await asyncio.sleep(60)
            await test_selective_regeneration()
            report.line("\n  Waiting 1 minute between tests...")
            await asyncio.sleep(60)
            await test_complex_requirements_case()
    finally:
        report.close()
        print(f"\n📄 Full report saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
