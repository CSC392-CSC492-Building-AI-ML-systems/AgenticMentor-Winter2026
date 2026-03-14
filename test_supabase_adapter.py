#!/usr/bin/env python3
"""
Test script for SupabaseAdapter - verifies connection and basic CRUD operations.

Usage:
    python test_supabase_adapter.py

Prerequisites:
    1. Run the migration SQL in Supabase Dashboard
    2. Set SUPABASE_URL and SUPABASE_KEY in .env file
    3. Install dependencies: pip install -r requirements.txt
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_connection():
    """Test 1: Verify Supabase connection."""
    print("\n" + "="*70)
    print("TEST 1: Supabase Connection")
    print("="*70)
    
    try:
        from src.orchestrator.supabase_adapter import create_supabase_adapter
        
        adapter = create_supabase_adapter()
        print("✅ SupabaseAdapter initialized successfully")
        print(f"   URL: {adapter.url}")
        print(f"   Key: {adapter.key[:20]}...")
        
        return adapter
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Run: pip install supabase")
        return None
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("   Check your .env file for SUPABASE_URL and SUPABASE_KEY")
        return None
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


async def test_save_and_load(adapter):
    """Test 2: Save and load a project state."""
    print("\n" + "="*70)
    print("TEST 2: Save and Load Project State")
    print("="*70)
    
    test_session_id = f"test-session-{int(datetime.now().timestamp())}"
    
    # Create test state
    test_state = {
        "session_id": test_session_id,
        "project_name": "Test Project",
        "current_phase": "initialization",
        "requirements": {
            "project_type": "web application",
            "functional": ["user authentication", "dashboard"],
            "target_users": ["developers"],
            "is_complete": False,
            "progress": 0.3,
        },
        "architecture": {
            "tech_stack": {
                "frontend": "React",
                "backend": "FastAPI",
                "database": "PostgreSQL"
            }
        },
        "conversation_history": [
            {"role": "user", "content": "I want to build a web app"},
            {"role": "assistant", "content": "Great! Let's gather requirements."},
        ],
        "mockups": [],
        "roadmap": {"phases": [], "milestones": []},
        "agent_interactions": {},
        "decisions": ["Use FastAPI for fast development"],
        "assumptions": ["Users have modern browsers"],
        "export_artifacts": {},
    }
    
    try:
        # Save
        print(f"📝 Saving test session: {test_session_id}")
        await adapter.save(test_session_id, test_state)
        print("✅ Save successful")
        
        # Load
        print(f"📖 Loading test session: {test_session_id}")
        loaded_state = await adapter.get(test_session_id)
        
        if loaded_state:
            print("✅ Load successful")
            print(f"   Project name: {loaded_state.get('project_name')}")
            print(f"   Current phase: {loaded_state.get('current_phase')}")
            print(f"   Requirements progress: {loaded_state['requirements']['progress']}")
            print(f"   Tech stack: {loaded_state['architecture']['tech_stack']}")
            print(f"   Conversation messages: {len(loaded_state['conversation_history'])}")
            print(f"   Decisions: {len(loaded_state.get('decisions', []))}")
            
            # Verify data integrity
            assert loaded_state["session_id"] == test_session_id
            assert loaded_state["project_name"] == "Test Project"
            assert loaded_state["requirements"]["progress"] == 0.3
            assert len(loaded_state["conversation_history"]) == 2
            print("✅ Data integrity verified")
            
        else:
            print("❌ Load returned None")
            
        return test_session_id
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_update(adapter, session_id):
    """Test 3: Update existing project state."""
    print("\n" + "="*70)
    print("TEST 3: Update Project State (Delta)")
    print("="*70)
    
    try:
        # Load existing state
        state = await adapter.get(session_id)
        if not state:
            print("❌ Session not found")
            return
        
        # Update requirements
        state["requirements"]["progress"] = 0.8
        state["requirements"]["is_complete"] = True
        state["current_phase"] = "requirements_complete"
        
        # Add conversation message
        state["conversation_history"].append({
            "role": "user",
            "content": "Requirements look good!",
        })
        
        # Save updated state
        print("📝 Updating state...")
        await adapter.save(session_id, state)
        print("✅ Update successful")
        
        # Reload and verify
        updated_state = await adapter.get(session_id)
        print(f"   Requirements complete: {updated_state['requirements']['is_complete']}")
        print(f"   Progress: {updated_state['requirements']['progress']}")
        print(f"   Current phase: {updated_state['current_phase']}")
        print(f"   Total messages: {len(updated_state['conversation_history'])}")
        
        assert updated_state["requirements"]["progress"] == 0.8
        assert len(updated_state["conversation_history"]) == 3
        print("✅ Update verified")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_mockups(adapter, session_id):
    """Test 4: Save and merge mockups (identity-based)."""
    print("\n" + "="*70)
    print("TEST 4: Mockups Identity-Based Merge")
    print("="*70)
    
    try:
        # Load state
        state = await adapter.get(session_id)
        
        # Add first mockup
        state["mockups"] = [
            {
                "screen_id": "login",
                "screen_name": "Login Screen",
                "wireframe_spec": {
                    "components": [
                        {"type": "form", "label": "Sign In", "children": ["Email", "Password"]}
                    ]
                },
                "template_used": "auth",
                "interactions": ["submit_login"],
            }
        ]
        
        await adapter.save(session_id, state)
        print("✅ Saved 1 mockup")
        
        # Add second mockup
        state = await adapter.get(session_id)
        state["mockups"].append({
            "screen_id": "dashboard",
            "screen_name": "Dashboard",
            "wireframe_spec": {
                "components": [
                    {"type": "header", "label": "Welcome"},
                    {"type": "card_grid", "label": "Stats"}
                ]
            },
            "template_used": "dashboard",
            "interactions": [],
        })
        
        await adapter.save(session_id, state)
        print("✅ Saved 2 mockups")
        
        # Update first mockup (identity-based merge)
        state = await adapter.get(session_id)
        state["mockups"][0]["screen_name"] = "Login Screen (Updated)"
        state["mockups"][0]["interactions"] = ["submit_login", "forgot_password"]
        
        await adapter.save(session_id, state)
        print("✅ Updated existing mockup")
        
        # Verify
        final_state = await adapter.get(session_id)
        print(f"   Total mockups: {len(final_state['mockups'])}")
        
        login_screen = next(m for m in final_state["mockups"] if m["screen_id"] == "login")
        print(f"   Login screen name: {login_screen['screen_name']}")
        print(f"   Login interactions: {login_screen['interactions']}")
        
        assert len(final_state["mockups"]) == 2
        assert login_screen["screen_name"] == "Login Screen (Updated)"
        assert len(login_screen["interactions"]) == 2
        print("✅ Identity-based merge verified")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_list_sessions(adapter):
    """Test 5: List all sessions."""
    print("\n" + "="*70)
    print("TEST 5: List All Sessions")
    print("="*70)
    
    try:
        sessions = await adapter.list_sessions()
        print(f"✅ Found {len(sessions)} session(s)")
        for i, session_id in enumerate(sessions[:5], 1):
            print(f"   {i}. {session_id}")
        
        if len(sessions) > 5:
            print(f"   ... and {len(sessions) - 5} more")
            
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_cleanup(adapter, session_id):
    """Test 6: Delete test session."""
    print("\n" + "="*70)
    print("TEST 6: Cleanup (Delete Test Session)")
    print("="*70)
    
    try:
        await adapter.delete(session_id)
        print(f"✅ Deleted test session: {session_id}")
        
        # Verify deletion
        state = await adapter.get(session_id)
        assert state is None
        print("✅ Deletion verified (session no longer exists)")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("SupabaseAdapter Test Suite")
    print("="*70)
    
    # Test 1: Connection
    adapter = await test_connection()
    if not adapter:
        print("\n❌ FAILED: Cannot proceed without valid connection")
        sys.exit(1)
    
    # Test 2: Save and Load
    session_id = await test_save_and_load(adapter)
    if not session_id:
        print("\n❌ FAILED: Save/Load test failed")
        sys.exit(1)
    
    # Test 3: Update
    await test_update(adapter, session_id)
    
    # Test 4: Mockups
    await test_mockups(adapter, session_id)
    
    # Test 5: List
    await test_list_sessions(adapter)
    
    # Test 6: Cleanup
    await test_cleanup(adapter, session_id)
    
    # Summary
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED")
    print("="*70)
    print("\nSupabaseAdapter is ready to use!")
    print("\nNext steps:")
    print("1. The adapter will be used automatically when SUPABASE_URL and SUPABASE_KEY are set")
    print("2. Test with requirements_collector agent: python run_requirements_agent.py")
    print("3. Verify data persists in Supabase Dashboard > Table Editor")


if __name__ == "__main__":
    asyncio.run(main())
