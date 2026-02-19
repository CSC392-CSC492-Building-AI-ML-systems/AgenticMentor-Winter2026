"""Simple script to run the Execution Planner Agent."""

import asyncio
import json
from src.agents.execution_planner_agent import ExecutionPlannerAgent
from src.state.project_state import ArchitectureDefinition


async def main():
    # Create the agent (no LLM needed - uses fallback)
    agent = ExecutionPlannerAgent()
    
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
    
    # Context with architecture (required input)
    context = {
        "architecture": architecture,
        "requirements": {
            "functional": ["User authentication", "Dashboard"],
            "constraints": ["Python backend"]
        }
    }
    
    # Run the agent
    print("Running Execution Planner Agent...")
    output = await agent.execute(
        input={},  # Can be empty or contain user request
        context=context,
        tools=[]
    )
    
    # Print results
    print("\n" + "="*60)
    print("EXECUTION PLAN OUTPUT")
    print("="*60)
    
    execution_plan = output.content.get("execution_plan", {})
    
    print(f"\nPhases ({len(execution_plan.get('phases', []))}):")
    for phase in execution_plan.get("phases", []):
        print(f"  - {phase.get('name')}: {phase.get('description', '')}")
    
    print(f"\nMilestones ({len(execution_plan.get('milestones', []))}):")
    for milestone in execution_plan.get("milestones", []):
        print(f"  - {milestone.get('name')}: {milestone.get('description', '')}")
    
    print(f"\nImplementation Tasks ({len(execution_plan.get('implementation_tasks', []))}):")
    for task in execution_plan.get("implementation_tasks", []):
        deps = ", ".join(task.get("depends_on", [])) or "none"
        print(f"  [{task.get('id')}] {task.get('title')}")
        print(f"      Phase: {task.get('phase_name')}")
        print(f"      Depends on: {deps}")
        if task.get("external_resources"):
            print(f"      Resources: {', '.join(task.get('external_resources', []))}")
    
    if execution_plan.get("critical_path"):
        print(f"\nCritical Path: {execution_plan.get('critical_path')}")
    
    print(f"\nExternal Resources: {', '.join(execution_plan.get('external_resources', []))}")
    
    print("\n" + "="*60)
    print("STATE DELTA (for state manager):")
    print("="*60)
    print(json.dumps(output.state_delta, indent=2))
    
    print("\n" + "="*60)
    print("METADATA:")
    print("="*60)
    print(json.dumps(output.metadata, indent=2))
    
    return output


if __name__ == "__main__":
    result = asyncio.run(main())
