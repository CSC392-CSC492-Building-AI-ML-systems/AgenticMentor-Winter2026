"""Integration test for ProjectArchitectAgent with live Gemini API."""

import asyncio
import sys
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

# Simple scenario: minimal requirements
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
        "constraints": ["Must use Python for backend"],
    }
}

# Complex scenario: B2B-style app with more moving parts
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
            {"role": "Org Admin", "goal": "Configure SSO and manage org members", "reason": "Security and onboarding"},
            {"role": "Project Manager", "goal": "Create projects and assign tasks with due dates", "reason": "Planning"},
        ],
    }
}

# Which scenario(s) to run: "simple" (3 LLM calls), "complex", or "both" (6 calls, default).
# Gemini free tier ~20 req/min; use "simple" to avoid 429: python ... simple
RUN_MODE = (sys.argv[1] if len(sys.argv) > 1 else "both").lower()
if RUN_MODE not in ("simple", "complex", "both"):
    RUN_MODE = "both"


class MockPersistenceAdapter:
    """In-memory mock for StateManager's persistence layer."""

    def __init__(self):
        self._store: dict = {}

    async def get(self, session_id: str) -> dict | None:
        return self._store.get(session_id)

    async def save(self, session_id: str, data: dict) -> None:
        self._store[session_id] = data


async def main():
    print("=" * 60)
    print("ProjectArchitectAgent Integration Test")
    print("=" * 60)
    print(f"Run mode: {RUN_MODE}")

    from src.state.state_manager import StateManager
    llm = GeminiClient(model="gemini-2.5-flash")
    persistence = MockPersistenceAdapter()
    state_manager = StateManager(persistence_adapter=persistence)
    agent = ProjectArchitectAgent(state_manager=state_manager, llm_client=llm)

    scenarios = []
    if RUN_MODE in ("simple", "both"):
        scenarios.append(("simple", SIMPLE_REQUIREMENTS))
    if RUN_MODE in ("complex", "both"):
        scenarios.append(("complex", COMPLEX_REQUIREMENTS))

    out_dir = project_root / "test_output"
    out_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    written = []

    for label, test_input in scenarios:
        req = test_input["requirements"]
        print("\n" + "=" * 60)
        print(f"Scenario: {label.upper()}")
        print("=" * 60)
        print("\n📋 Input Requirements:")
        print(f"   Functional: {len(req.get('functional', []))} items")
        print(f"   Non-Functional: {len(req.get('non_functional', []))} items")
        print(f"   Constraints: {len(req.get('constraints', []))} items")
        if req.get("user_stories"):
            print(f"   User stories: {len(req['user_stories'])} items")
        print("\n🔄 Running ProjectArchitectAgent.process()...")
        print("-" * 60)

        try:
            result = await agent.process(test_input)
        except Exception as e:
            print(f"\n❌ Error ({label}): {type(e).__name__}: {e}")
            raise

        print("\n✅ Agent completed successfully!")
        print("-" * 60)

        if "state_delta" in result and "architecture" in result["state_delta"]:
            arch = result["state_delta"]["architecture"]
            print("\n📐 Architecture Output:")
            if arch.get("tech_stack"):
                for key, value in arch["tech_stack"].items():
                    print(f"   {key}: {value}")
            if arch.get("system_diagram"):
                d = arch["system_diagram"]
                print(f"\n   System Diagram (first 150 chars): {d[:150]}..." if len(d) > 150 else f"\n   System Diagram: {d}")
            if arch.get("data_schema"):
                d = arch["data_schema"]
                print(f"   ERD (first 150 chars): {d[:150]}..." if len(d) > 150 else f"   ERD: {d}")
            if arch.get("deployment_strategy"):
                print(f"\n   Deployment: {arch['deployment_strategy']}")

        suffix = f"{timestamp}_{label}"
        full_path = out_dir / f"architect_full_output_{suffix}.txt"
        system_mmd = out_dir / f"system_diagram_{suffix}.mmd"
        erd_mmd = out_dir / f"erd_diagram_{suffix}.mmd"

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(f"ProjectArchitectAgent – Full Output ({label})\n")
            f.write("=" * 60 + "\n\n")
            if result.get("summary"):
                f.write("Summary:\n")
                f.write(result["summary"] + "\n\n")
            if "state_delta" in result and "architecture" in result["state_delta"]:
                arch = result["state_delta"]["architecture"]
                f.write("Tech Stack:\n")
                for k, v in arch.get("tech_stack", {}).items():
                    f.write(f"  {k}: {v}\n")
                f.write("\n")
                if arch.get("tech_stack_rationale"):
                    f.write("Tech Stack Rationale:\n")
                    f.write(arch["tech_stack_rationale"] + "\n\n")
                if arch.get("deployment_strategy"):
                    f.write("Deployment:\n")
                    f.write(f"  {arch['deployment_strategy']}\n\n")
                if arch.get("system_diagram"):
                    f.write("System Diagram (Mermaid):\n")
                    f.write("-" * 40 + "\n")
                    f.write(arch["system_diagram"])
                    f.write("\n\n")
                if arch.get("data_schema"):
                    f.write("ERD Diagram (Mermaid):\n")
                    f.write("-" * 40 + "\n")
                    f.write(arch["data_schema"])
                    f.write("\n")

        if result.get("state_delta", {}).get("architecture", {}).get("system_diagram"):
            with open(system_mmd, "w", encoding="utf-8") as f:
                f.write(result["state_delta"]["architecture"]["system_diagram"])
        if result.get("state_delta", {}).get("architecture", {}).get("data_schema"):
            with open(erd_mmd, "w", encoding="utf-8") as f:
                f.write(result["state_delta"]["architecture"]["data_schema"])

        print("\n📁 Full output written to:")
        print(f"   {full_path}")
        print(f"   {system_mmd}")
        print(f"   {erd_mmd}")

    print("\n" + "=" * 60)
    print("Test completed.")


if __name__ == "__main__":
    asyncio.run(main())
