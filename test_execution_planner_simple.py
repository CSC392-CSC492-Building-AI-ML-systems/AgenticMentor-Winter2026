"""Conversational test for ExecutionPlannerAgent — three back-and-forth turns."""

import asyncio
import sys
import io
import json

from src.agents.execution_planner_agent import ExecutionPlannerAgent
from src.utils.config import settings

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Shared project context (architecture + requirements stay constant)
# ---------------------------------------------------------------------------
ARCHITECTURE = {
    "tech_stack": {
        "frontend": "React 18",
        "backend": "FastAPI (Python)",
        "database": "PostgreSQL 16",
        "devops": "Docker + GitHub Actions",
    },
    "api_design": [
        {"method": "GET",  "path": "/api/users",     "description": "List users"},
        {"method": "POST", "path": "/api/users",     "description": "Create user"},
        {"method": "POST", "path": "/api/auth/login","description": "Login"},
        {"method": "GET",  "path": "/api/dashboard", "description": "Fetch dashboard data"},
    ],
    "deployment_strategy": "AWS ECS with RDS PostgreSQL",
}

REQUIREMENTS = {
    "functional": [
        "User authentication (register/login/logout)",
        "Dashboard with real-time metrics",
        "User role management (admin/viewer)",
    ],
    "non_functional": ["< 200 ms API response", "99.9% uptime SLA"],
    "constraints": ["Python backend", "Must use PostgreSQL"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _section(title: str) -> None:
    print(f"\n{'=' * 65}")
    print(f"  {title}")
    print(f"{'=' * 65}")


def _print_roadmap(roadmap: dict, label: str = "") -> None:
    phases = roadmap.get("phases", [])
    milestones = roadmap.get("milestones", [])
    tasks = roadmap.get("implementation_tasks", [])
    sprints = roadmap.get("sprints", [])

    print(f"\n--- {label} ---" if label else "")
    print(f"  Phases      : {len(phases)}  -> {[p['name'] for p in phases]}")
    print(f"  Milestones  : {len(milestones)}  -> {[m['name'] for m in milestones]}")
    print(f"  Tasks       : {len(tasks)}")
    for t in tasks:
        deps = ", ".join(t.get("depends_on") or []) or "none"
        print(f"    [{t['id']}] {t['title']}  (phase: {t.get('phase_name','?')})")
    print(f"  Sprints     : {len(sprints)}")
    for s in sprints:
        print(f"    {s['name']} ({len(s.get('tasks', []))} tasks): {s.get('goal','')}")
    cp = roadmap.get("critical_path", "")
    if cp:
        print(f"  Critical Path: {cp.replace('→', '->')}")


def _validate_state_delta(delta: dict, turn: int) -> bool:
    required = {"roadmap", "roadmap.phases", "roadmap.milestones", "roadmap.implementation_tasks"}
    missing = required - set(delta.keys())
    if missing:
        print(f"  [FAIL] Turn {turn}: state_delta missing keys: {missing}")
        return False
    print(f"  [OK] Turn {turn}: state_delta has all required keys: {sorted(delta.keys())}")
    return True


def _compare_phases(prev: dict, curr: dict) -> None:
    """Show whether phases were preserved or regenerated."""
    prev_names = [p["name"] for p in prev.get("phases", [])]
    curr_names = [p["name"] for p in curr.get("phases", [])]
    if prev_names == curr_names:
        print("  [PRESERVED] Phases unchanged.")
    else:
        added   = set(curr_names) - set(prev_names)
        removed = set(prev_names) - set(curr_names)
        print(f"  [CHANGED] Phases: added={added or '{}'}, removed={removed or '{}'}")


def _compare_tasks(prev: dict, curr: dict) -> None:
    prev_ids = {t["id"] for t in prev.get("implementation_tasks", [])}
    curr_ids = {t["id"] for t in curr.get("implementation_tasks", [])}
    if prev_ids == curr_ids:
        print(f"  [PRESERVED] Tasks unchanged ({len(curr_ids)} tasks).")
    else:
        added   = curr_ids - prev_ids
        removed = prev_ids - curr_ids
        print(
            f"  [CHANGED] Tasks: {len(curr_ids)} total | "
            f"+{len(added)} added, -{len(removed)} removed"
        )


def _compare_sprints(prev: dict, curr: dict) -> None:
    prev_n = len(prev.get("sprints", []))
    curr_n = len(curr.get("sprints", []))
    if prev_n == curr_n:
        print(f"  [PRESERVED?] Sprint count same ({curr_n}).")
    else:
        print(f"  [CHANGED] Sprints: {prev_n} -> {curr_n}")


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------

async def run_conversation():
    _section("Initializing Execution Planner Agent")
    print(f"  Model: Gemini {settings.model_name}")
    agent = ExecutionPlannerAgent(state_manager=None, llm_client=None)
    print("  Agent ready.")

    all_pass = True

    # -----------------------------------------------------------------------
    # TURN 1 — full generation (no existing roadmap)
    # -----------------------------------------------------------------------
    _section("TURN 1: Initial plan generation")
    print("  User: (new project — generate a full execution plan)")

    output1 = await agent.execute(
        input={},
        context={"architecture": ARCHITECTURE, "requirements": REQUIREMENTS},
        tools=[],
    )

    roadmap1 = (output1.content or {}).get("roadmap") or {}
    _print_roadmap(roadmap1, "Turn 1 roadmap")
    ok1 = _validate_state_delta(output1.state_delta, turn=1)
    all_pass = all_pass and ok1
    print(f"\n  Review score : {output1.metadata.get('review_score', 'N/A')}")
    print(f"  Attempts     : {output1.metadata.get('attempts', 'N/A')}")

    # -----------------------------------------------------------------------
    # TURN 2 — selective: add more QA tasks
    # -----------------------------------------------------------------------
    _section("TURN 2: Add more QA/testing tasks")
    user_msg_2 = "Add more testing tasks — we need unit tests, integration tests, and performance benchmarks"
    print(f"  User: \"{user_msg_2}\"")
    print("  Expected: phases + milestones PRESERVED; tasks + sprints REGENERATED")

    output2 = await agent.execute(
        input={"user_request": user_msg_2},
        context={
            "architecture":    ARCHITECTURE,
            "requirements":    REQUIREMENTS,
            "existing_roadmap": roadmap1,
        },
        tools=[],
    )

    roadmap2 = (output2.content or {}).get("roadmap") or {}
    _print_roadmap(roadmap2, "Turn 2 roadmap")
    ok2 = _validate_state_delta(output2.state_delta, turn=2)
    all_pass = all_pass and ok2

    print("\n  Diff vs Turn 1:")
    _compare_phases(roadmap1, roadmap2)
    _compare_tasks(roadmap1, roadmap2)
    _compare_sprints(roadmap1, roadmap2)
    print(f"\n  Review score : {output2.metadata.get('review_score', 'N/A')}")
    print(f"  Attempts     : {output2.metadata.get('attempts', 'N/A')}")

    # -----------------------------------------------------------------------
    # TURN 3 — selective: reorganize sprints only
    # -----------------------------------------------------------------------
    _section("TURN 3: Reorganize sprints only")
    user_msg_3 = "Reorganize only the sprints — group them into exactly 3 sprints"
    print(f"  User: \"{user_msg_3}\"")
    print("  Expected: phases + milestones + tasks PRESERVED; sprints REGENERATED")

    output3 = await agent.execute(
        input={"user_request": user_msg_3},
        context={
            "architecture":    ARCHITECTURE,
            "requirements":    REQUIREMENTS,
            "existing_roadmap": roadmap2,
        },
        tools=[],
    )

    roadmap3 = (output3.content or {}).get("roadmap") or {}
    _print_roadmap(roadmap3, "Turn 3 roadmap")
    ok3 = _validate_state_delta(output3.state_delta, turn=3)
    all_pass = all_pass and ok3

    print("\n  Diff vs Turn 2:")
    _compare_phases(roadmap2, roadmap3)
    _compare_tasks(roadmap2, roadmap3)
    _compare_sprints(roadmap2, roadmap3)
    print(f"\n  Review score : {output3.metadata.get('review_score', 'N/A')}")
    print(f"  Attempts     : {output3.metadata.get('attempts', 'N/A')}")

    # -----------------------------------------------------------------------
    # Final state delta check
    # -----------------------------------------------------------------------
    _section("Final state_delta (Turn 3)")
    for key, val in output3.state_delta.items():
        if isinstance(val, list):
            print(f"  {key}: [{len(val)} items]")
        elif isinstance(val, dict):
            print(f"  {key}: {{...}} ({len(val)} top-level keys)")
        else:
            print(f"  {key}: {val}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    _section("TEST SUMMARY")
    print(f"  Turn 1 (full generation)         : {'PASS' if ok1 else 'FAIL'}")
    print(f"  Turn 2 (add QA tasks)            : {'PASS' if ok2 else 'FAIL'}")
    print(f"  Turn 3 (reorganize sprints only) : {'PASS' if ok3 else 'FAIL'}")
    print(f"\n  Overall: {'ALL PASS' if all_pass else 'SOME FAILURES'}")
    return all_pass


if __name__ == "__main__":
    ok = asyncio.run(run_conversation())
    sys.exit(0 if ok else 1)
