"""Simple script to run the Execution Planner Agent."""

import asyncio
import json
import sys
import io
from src.agents.execution_planner_agent import ExecutionPlannerAgent
from src.utils.config import settings

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


async def main():
    print(f"Initializing Execution Planner Agent with LLM (Gemini {settings.model_name})...")
    # state_manager is optional; omit for standalone testing
    agent = ExecutionPlannerAgent(state_manager=None, llm_client=None)

    # Example architecture from Architect agent output
    architecture = {
        "tech_stack": {
            "frontend": "React",
            "backend": "FastAPI",
            "database": "PostgreSQL",
            "devops": "Docker"
        },
        "api_design": [
            {"method": "GET", "path": "/api/users", "description": "List users"},
            {"method": "POST", "path": "/api/users", "description": "Create user"}
        ],
        "deployment_strategy": "AWS ECS with RDS"
    }

    # Context with architecture (required input) and requirements
    context = {
        "architecture": architecture,
        "requirements": {
            "functional": ["User authentication", "Dashboard"],
            "constraints": ["Python backend"]
        }
    }

    # Run the agent via execute() — delegates to process() internally
    print("Running Execution Planner Agent...")
    output = await agent.execute(
        input={},
        context=context,
        tools=[]
    )

    # Print results
    print("\n" + "=" * 60)
    print("EXECUTION PLAN OUTPUT")
    print("=" * 60)

    content = output.content or {}
    summary = content.get("summary", "")
    if summary:
        print(f"\nSummary: {summary}")

    roadmap = content.get("roadmap") or content.get("execution_plan") or {}

    print(f"\nPhases ({len(roadmap.get('phases', []))}):")
    for phase in roadmap.get("phases", []):
        print(f"  [{phase.get('order', '?')}] {phase.get('name')}: {phase.get('description', '')}")

    print(f"\nMilestones ({len(roadmap.get('milestones', []))}):")
    for milestone in roadmap.get("milestones", []):
        date = milestone.get("target_date") or "TBD"
        print(f"  - {milestone.get('name')} ({date}): {milestone.get('description', '')}")

    print(f"\nImplementation Tasks ({len(roadmap.get('implementation_tasks', []))}):")
    for task in roadmap.get("implementation_tasks", []):
        deps = ", ".join(task.get("depends_on", [])) or "none"
        print(f"  [{task.get('id')}] {task.get('title')}")
        print(f"      Phase: {task.get('phase_name')}  |  Milestone: {task.get('milestone_name') or 'N/A'}")
        print(f"      Depends on: {deps}")
        if task.get("external_resources"):
            print(f"      Resources: {', '.join(task.get('external_resources', []))}")

    print(f"\nSprints ({len(roadmap.get('sprints', []))}):")
    for sprint in roadmap.get("sprints", []):
        print(f"  {sprint.get('name')}: {sprint.get('goal', '')} ({len(sprint.get('tasks', []))} tasks)")

    if roadmap.get("critical_path"):
        critical_path = roadmap.get("critical_path", "").replace("→", "->")
        print(f"\nCritical Path: {critical_path}")

    if roadmap.get("external_resources"):
        print(f"\nExternal Resources: {', '.join(roadmap.get('external_resources', []))}")

    print("\n" + "=" * 60)
    print("STATE DELTA (keys written to state manager):")
    print("=" * 60)
    for key in output.state_delta:
        value = output.state_delta[key]
        if isinstance(value, list):
            print(f"  {key}: [{len(value)} items]")
        elif isinstance(value, dict):
            print(f"  {key}: {{...}}")
        else:
            print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("METADATA:")
    print("=" * 60)
    print(json.dumps(output.metadata, indent=2))

    return output


if __name__ == "__main__":
    result = asyncio.run(main())
