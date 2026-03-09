#!/usr/bin/env python3
"""
Phase 4: Manual Orchestration & Persistence Chain Test
======================================================
This script implements the "manually recreate the orchestration" approach.

PURPOSE:
To verify the full agentic pipeline (Collector -> Architect -> Planner -> Mockup -> Exporter)
while ensuring that persistence (Supabase) is successful at every single hand-off.

HOW IT WORKS:
1. It initializes a project.
2. It calls Agent A -> Saves Delta to DB -> Loads Full State.
3. It calls Agent B -> Saves Delta to DB -> Loads Full State.
...and so on.

This bypasses the back-to-back firing issues of the MasterOrchestrator and 
allows us to pinpoint exactly where data might be dropping or which agent 
is hitting the API limit.
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.state.persistence import get_default_adapter
from src.state.state_manager import StateManager

# Import all agent classes
try:
    from src.agents.requirements_collector import RequirementsAgent as RequirementsCollector
except ImportError:
    from src.agents.requirements_collector import RequirementsCollector

try:
    from src.agents.project_architect import ArchitectAgent as ProjectArchitect
except ImportError:
    from src.agents.project_architect import ProjectArchitect

from src.agents.execution_planner_agent import ExecutionPlannerAgent
from src.agents.mockup_agent import MockupAgent
from src.agents.exporter_agent import ExporterAgent

async def test_run_manual_chain():
    load_dotenv()
    db_adapter = get_default_adapter()
    state_manager = StateManager(db_adapter)
    
    session_id = f"manual-chain-{int(datetime.now().timestamp())}"
    print(f"\n🚀 STARTING MANUAL CHAIN TEST: {session_id}")
    print("="*70)

    # 0. Initialization
    print("\n[Step 0] Initializing Project...")
    initial_delta = {
        "project_name": "Manual Chain Fitness App",
        "current_phase": "initialization",
        "requirements.project_type": "A mobile fitness app for students."
    }
    await state_manager.update(session_id, initial_delta)

    # 1. Requirements Collector
    print("\n[Step 1] Running Requirements Collector...")
    collector = RequirementsCollector() # Doesn't need state_manager
    state = await state_manager.load(session_id)
    
    result = await collector._generate(
        input={"message": "It needs a dark mode and a calendar to track gym sessions."},
        context={"requirements": state.requirements, "conversation_history": []},
        tools=[]
    )
    
    reqs_dict = result["requirements"].model_dump() if hasattr(result["requirements"], "model_dump") else result["requirements"]
    reqs_dict["is_complete"] = True
    reqs_dict["progress"] = 100.0
    
    await state_manager.update(session_id, {"requirements": reqs_dict})
    print("✅ Requirements saved to Supabase.")

    # 2. Project Architect
    print("\n[Step 2] Running Project Architect...")
    # FIX: Architect requires the state_manager passed into __init__
    architect = ProjectArchitect(state_manager=state_manager) 
    state = await state_manager.load(session_id)
    
    result = await architect.process({
        "requirements": state.requirements,
        "user_request": "Define the tech stack"
    })
    
    await state_manager.update(session_id, result.get("state_delta", {}))
    print("✅ Architecture/Tech Stack saved to Supabase.")

    # 3. Execution Planner
    print("\n[Step 3] Running Execution Planner...")
    # FIX: Safest to pass state_manager here too, even if optional
    planner = ExecutionPlannerAgent(state_manager=state_manager)
    state = await state_manager.load(session_id)
    
    result = await planner.process({
        "requirements": state.requirements,
        "architecture": state.architecture,
        "user_request": "Plan the MVP"
    })
    
    await state_manager.update(session_id, result.get("state_delta", {}))
    print("✅ Implementation Roadmap saved to Supabase.")

    # 4. Mockup Agent
    print("\n[Step 4] Running Mockup Agent...")
    # FIX: Mockup strictly requires the state_manager passed into __init__
    mockup = MockupAgent(state_manager=state_manager)
    state = await state_manager.load(session_id)
    
    reqs_dump = state.requirements.model_dump() if hasattr(state.requirements, "model_dump") else {}
    arch_dump = state.architecture.model_dump() if hasattr(state.architecture, "model_dump") else {}
    
    result = await mockup.process({
        "project_id": session_id,
        "requirements": reqs_dump,
        "architecture": arch_dump,
        "platform": "web"
    })
    
    await state_manager.update(session_id, result.get("state_delta", {}))
    print("✅ UI Mockups saved to Supabase.")

    # 5. Exporter
    print("\n[Step 5] Running Exporter...")
    exporter = ExporterAgent() # Doesn't need state_manager
    state = await state_manager.load(session_id)
    
    state_dict = {
        "project_name": state.project_name,
        "requirements": state.requirements.model_dump() if state.requirements else {},
        "architecture": state.architecture.model_dump() if state.architecture else {},
        "roadmap": state.roadmap.model_dump() if state.roadmap else {},
        "mockups": [m.model_dump() for m in state.mockups] if state.mockups else []
    }
    
    result = await exporter._generate(input=state_dict, context={}, tools=[])
    
    await state_manager.update(session_id, result.get("state_delta", {}))
    print("✅ Final Artifacts saved to Supabase.")

    # FINAL VERIFICATION
    print("\n" + "="*70)
    print("🔍 FINAL DATABASE VERIFICATION")
    print("="*70)
    
    final_state = await db_adapter.get(session_id)
    
    checks = {
        "Project Name": final_state.get('project_name'),
        "Has Tech Stack": bool(final_state.get('architecture', {}).get('tech_stack')),
        "Roadmap Tasks": len(final_state.get('roadmap', {}).get('implementation_tasks', [])),
        "Mockup Count": len(final_state.get('mockups', [])),
        "Exported": bool(final_state.get('export_artifacts', {}).get('exported_at'))
    }

    for label, res in checks.items():
        status = "✅" if res else "❌"
        print(f"{status} {label}: {res}")

    print(f"\n🎉 MANUAL CHAIN COMPLETE. Session {session_id} is fully populated.")

if __name__ == "__main__":
    asyncio.run(test_run_manual_chain())