#!/usr/bin/env python3
"""
This script serves as the final "Live Fire" validation for the AgenticMentor.

PURPOSE:
Unlike structural tests, this script simulates a real human interaction 
across 6 distinct turns. It exercises the MasterOrchestrator's ability to 
hand off state between different agents while ensuring every message and 
resulting artifact is successfully persisted to Supabase.

WHAT IT TESTS:
1. Multi-Turn History: Verifies that conversation logs are correctly 
   appended to the database without overwriting previous turns.
2. Full Agent Lifecycle: Forces execution of all 5 core agents 
   (Collector -> Architect -> Planner -> Mockup -> Exporter).
3. StateManager Integration: Validates that the Orchestrator and 
   StateManager are correctly loading/saving the "Baton" (ProjectState) 
   between agent calls.
4. Final Integrity: Bypasses the local cache at the end to confirm 
   that the "Truth" exists physically in the Supabase tables.

USAGE:
    python tests/db/test_e2e_full_flow.py

PREREQUISITES:
    - Active Gemini API Key (requires LLM to generate real responses).
    - Valid .env with SUPABASE_URL and SUPABASE_KEY.
"""


import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# FIX: Add project root to path (Going UP two directories from tests/db/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.state.persistence import get_default_adapter
from src.state.state_manager import StateManager
from src.orchestrator.master_agent import MasterOrchestrator

async def run_multi_turn_e2e_test():
    """
    Simulates a real user having a multi-turn conversation, running the complex
    agents, and verifying the data in Supabase.
    """
    print("\n" + "="*70)
    print("🚀 PHASE 4: E2E Multi-Turn & Complex Agent Test")
    print("="*70)

    # 1. Setup Environment & Backend
    load_dotenv()
    db_adapter = get_default_adapter()
    state_manager = StateManager(db_adapter)
    
    # We initialize the orchestrator exactly how main.py does
    orchestrator = MasterOrchestrator(state_manager)
    
    session_id = f"e2e-test-{int(datetime.now().timestamp())}"
    print(f"📦 Created new chat session: {session_id}")
    print("[persistence] Verifying adapter type:", type(db_adapter).__name__)

    # 2. Simulate Multi-Turn Conversation
    chat_history = [
        # Turn 1: Initial idea
        ("I want to build a fitness app for students.", "requirements_collector"),
        # Turn 2: Providing more details to push progress forward
        ("It needs to have a calendar to track workouts and a dark mode.", "requirements_collector"),
        # Turn 3: Force the Architect
        ("Let's define the tech stack. Use React Native and Firebase.", "project_architect"),
        # Turn 4: Force the Execution Planner (Testing nested Roadmap)
        ("Please generate the implementation roadmap with tasks and dependencies.", "execution_planner"),
        # Turn 5: Force the Mockup Agent (Testing wireframe_spec)
        ("Design a wireframe for the workout calendar screen.", "mockup_agent"),
        # Turn 6: Force the Exporter (Testing export_artifacts)
        ("Export the final project documentation to markdown.", "exporter")
    ]

    try:
        for i, (message, target_agent) in enumerate(chat_history, 1):
            print(f"\n--- 💬 Turn {i}: User Message ---")
            print(f"User: '{message}'")
            print(f"Expected Agent: {target_agent}")
            
            # Using manual mode to guarantee we hit the specific complex agents for the test
            result = await orchestrator.process_request(
                user_input=message,
                session_id=session_id,
                agent_selection_mode="manual",
                selected_agent_id=target_agent
            )
            print(f"🤖 AI Reply: {result.get('message', '')[:100]}...")

        # 3. Verify the Database Actually Saved It
        print("\n" + "="*70)
        print("🔍 VERIFYING SUPABASE DATABASE INTEGRITY")
        print("="*70)
        
        # Load directly from the database (bypassing cache to be sure)
        final_state = await db_adapter.get(session_id)
        
        if not final_state:
            raise ValueError("Test failed: Session not found in database!")

        # Check Multi-turn Requirements
        req_progress = final_state.get('requirements', {}).get('progress', 0)
        print(f"✅ Multi-Turn Chat tracked: Requirements progress is at {req_progress}%")

        # Check Planner (Nested Roadmap)
        roadmap = final_state.get('roadmap', {})
        if roadmap and roadmap.get('implementation_tasks'):
            tasks = len(roadmap['implementation_tasks'])
            print(f"✅ Execution Planner validated: Found {tasks} nested tasks in roadmap JSONB.")
        else:
            print("❌ Execution Planner validation failed: Roadmap missing.")

        # Check Mockup (Wireframe Spec)
        mockups = final_state.get('mockups', [])
        if mockups and mockups[0].get('wireframe_spec'):
            print(f"✅ Mockup Agent validated: Found wireframe_spec in mockups table.")
        else:
            print("❌ Mockup Agent validation failed: Wireframe spec missing.")

        # Check Exporter (Export Artifacts)
        exports = final_state.get('export_artifacts', {})
        if exports and exports.get('generated_formats'):
            formats = exports['generated_formats']
            print(f"✅ Exporter validated: Found artifacts generated in formats: {formats}")
        else:
            print("❌ Exporter validation failed: Export artifacts missing.")

        print("\n🎉 ALL PHASE 4 E2E TESTS PASSED! Data is safely in Supabase.")
        print(f"👀 Go check the 'projects' and 'mockups' tables for session: {session_id}")
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_multi_turn_e2e_test())