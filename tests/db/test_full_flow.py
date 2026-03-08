#!/usr/bin/env python3
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# FIX: Add project root to path (Going UP two directories from tests/db/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.state.persistence import get_default_adapter

async def test_full_agent_integration():
    """Validates the complex outputs of the Planner, Mockup, and Exporter agents."""
    print("\n" + "="*70)
    print("PHASE 4: Full Agent Integration Test")
    print("="*70)

    # Load the environment variables from the .env file
    load_dotenv()

    adapter = get_default_adapter()
    session_id = f"integration-test-{int(datetime.now().timestamp())}"

    # Simulating the exact state delta structure the agents will push
    complex_state = {
        "session_id": session_id,
        "project_name": "Full Integration Test",
        "current_phase": "exportable",
        # 1. execution_planner output
        "roadmap": {
            "phases": [{"name": "Phase 1", "description": "Setup", "order": 1}],
            "milestones": [{"name": "MVP", "target_date": "2026-04-01"}],
            "implementation_tasks": [
                {
                    "id": "task-1",
                    "title": "Setup DB",
                    "depends_on": [],
                    "order": 1
                },
                {
                    "id": "task-2",
                    "title": "Build API",
                    "depends_on": ["task-1"], # Testing nested references
                    "order": 2
                }
            ],
            "sprints": [],
            "critical_path": "task-1 -> task-2",
            "external_resources": ["AWS"]
        },
        # 2. mockup_agent output
        "mockups": [
            {
                "screen_id": "settings",
                "screen_name": "Settings Page",
                "wireframe_spec": {"components": [{"type": "toggle", "label": "Dark Mode"}]},
                "template_used": "dashboard",
                "interactions": ["toggle_theme"],
                "version": "1.0"
            }
        ],
        # 3. exporter output
        "export_artifacts": {
            "executive_summary": "Project is ready.",
            "markdown_content": "# Project \n\n Details here.",
            "saved_path": "/exports/doc.md",
            "generated_formats": ["markdown", "pdf"],
            "exported_at": datetime.now().isoformat(),
            "history": []
        }
    }

    try:
        # 1. Save complex state
        print("📝 Saving complex multi-agent state...")
        await adapter.save(session_id, complex_state)
        
        # 2. Load and verify
        print("📖 Reading state back for verification...")
        loaded = await adapter.get(session_id)

        # 3. Assertions for execution_planner
        assert loaded["roadmap"]["critical_path"] == "task-1 -> task-2"
        assert len(loaded["roadmap"]["implementation_tasks"]) == 2
        assert loaded["roadmap"]["implementation_tasks"][1]["depends_on"][0] == "task-1"
        print("✅ execution_planner nested JSONB validated")

        # 4. Assertions for mockup_agent
        assert len(loaded["mockups"]) == 1
        assert loaded["mockups"][0]["screen_id"] == "settings"
        assert loaded["mockups"][0]["interactions"][0] == "toggle_theme"
        print("✅ mockup_agent identity merge & JSONB validated")

        # 5. Assertions for exporter
        assert "markdown" in loaded["export_artifacts"]["generated_formats"]
        assert loaded["export_artifacts"]["saved_path"] == "/exports/doc.md"
        print("✅ exporter artifacts validated")

        # Cleanup
        # await adapter.delete(session_id)
        # print("✅ Cleanup successful")

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_agent_integration())