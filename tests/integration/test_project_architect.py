"""Integration test for ProjectArchitectAgent with live Gemini API."""

import asyncio
import sys
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

    # Initialize components
    llm = GeminiClient(model="gemini-2.5-flash")  # Use flash for faster/cheaper testing
    
    # Create a minimal state manager with mock persistence
    from src.state.state_manager import StateManager
    persistence = MockPersistenceAdapter()
    state_manager = StateManager(persistence_adapter=persistence)

    # Instantiate the architect agent
    agent = ProjectArchitectAgent(
        state_manager=state_manager,
        llm_client=llm,
    )

    # Sample requirements for testing
    test_input = {
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

    print("\n📋 Input Requirements:")
    print(f"   Functional: {len(test_input['requirements']['functional'])} items")
    print(f"   Non-Functional: {len(test_input['requirements']['non_functional'])} items")
    print(f"   Constraints: {len(test_input['requirements']['constraints'])} items")

    print("\n🔄 Running ProjectArchitectAgent.process()...")
    print("-" * 60)

    try:
        result = await agent.process(test_input)

        print("\n✅ Agent completed successfully!")
        print("-" * 60)

        # Display results
        if "state_delta" in result:
            delta = result["state_delta"]
            
            if "architecture" in delta:
                arch = delta["architecture"]
                print("\n📐 Architecture Output:")
                
                if "tech_stack" in arch:
                    print("\n   Tech Stack:")
                    for key, value in arch.get("tech_stack", {}).items():
                        print(f"      {key}: {value}")
                
                if "diagrams" in arch:
                    print("\n   Diagrams Generated:")
                    for diagram_type, code in arch.get("diagrams", {}).items():
                        preview = code[:80] + "..." if len(str(code)) > 80 else code
                        print(f"      {diagram_type}: {preview}")
                
                # Show actual diagram fields (system_diagram and data_schema)
                if "system_diagram" in arch:
                    diagram = arch["system_diagram"]
                    print(f"\n   System Diagram (first 150 chars):")
                    print(f"      {diagram[:150]}..." if len(diagram) > 150 else f"      {diagram}")
                
                if "data_schema" in arch:
                    diagram = arch["data_schema"]
                    print(f"\n   ERD Diagram (first 150 chars):")
                    print(f"      {diagram[:150]}..." if len(diagram) > 150 else f"      {diagram}")
                
                if "deployment_strategy" in arch:
                    print(f"\n   Deployment: {arch.get('deployment_strategy')}")

        print("\n" + "=" * 60)
        print("Test completed.")
        return result  # Return for use in selective regen test

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        raise


async def test_selective_regeneration():
    """Test selective regeneration - only regenerate specific artifacts."""
    print("\n" + "=" * 60)
    print("Selective Regeneration Test")
    print("=" * 60)

    # Initialize components
    llm = GeminiClient(model="gemini-2.5-flash")
    
    from src.state.state_manager import StateManager
    persistence = MockPersistenceAdapter()
    state_manager = StateManager(persistence_adapter=persistence)

    agent = ProjectArchitectAgent(
        state_manager=state_manager,
        llm_client=llm,
    )

    # Step 1: Full generation
    print("\n🔄 Step 1: Full architecture generation...")
    test_input = {
        "requirements": {
            "functional": ["User login", "Dashboard", "REST API"],
            "constraints": ["Must use Python for backend"],
        }
    }
    
    result1 = await agent.process(test_input)
    arch1 = result1["architecture"]
    
    print(f"   Tech Stack: {arch1.get('tech_stack', {}).get('backend', 'N/A')}")
    print(f"   System Diagram: {'✓ generated' if arch1.get('system_diagram') else '✗ missing'}")
    print(f"   ERD: {'✓ generated' if arch1.get('data_schema') else '✗ missing'}")

    print("\nWaiting 4 minutes to avoid free-tier API rate limits...")
    await asyncio.sleep(240)

    # Step 2: Selective regeneration - only ERD
    print("\n🔄 Step 2: Selective regeneration (ERD only)...")
    print('   User request: "Please regenerate only the ERD diagram"')
    
    result2 = await agent.process({
        "requirements": test_input["requirements"],
        "existing_architecture": arch1,
        "user_request": "Please regenerate only the ERD diagram"
    })
    arch2 = result2["architecture"]

    # Compare results
    print("\n📊 Comparison:")
    
    tech_stack_preserved = arch2.get("tech_stack") == arch1.get("tech_stack")
    print(f"   Tech Stack preserved: {'✓ YES' if tech_stack_preserved else '✗ NO (regenerated)'}")
    
    system_diagram_preserved = arch2.get("system_diagram") == arch1.get("system_diagram")
    print(f"   System Diagram preserved: {'✓ YES' if system_diagram_preserved else '✗ NO (regenerated)'}")
    
    erd_changed = arch2.get("data_schema") != arch1.get("data_schema")
    print(f"   ERD regenerated: {'✓ YES' if erd_changed else '✗ NO (same as before)'}")

    # Step 3: Selective regeneration - tech stack (should cascade)
    print("\n🔄 Step 3: Selective regeneration (tech stack change)...")
    print('   User request: "Change the backend to Node.js with Express"')
    
    result3 = await agent.process({
        "requirements": test_input["requirements"],
        "existing_architecture": arch1,
        "user_request": "Change the backend to Node.js with Express"
    })
    arch3 = result3["architecture"]

    print("\n📊 Comparison (tech stack change should cascade):")
    
    tech_stack_changed = arch3.get("tech_stack") != arch1.get("tech_stack")
    print(f"   Tech Stack changed: {'✓ YES' if tech_stack_changed else '✗ NO'}")
    print(f"   New backend: {arch3.get('tech_stack', {}).get('backend', 'N/A')}")

    print("\n" + "=" * 60)
    print("Selective regeneration test completed.")
    print("=" * 60)


async def run_all_tests():
    """Run all integration tests."""
    await main()
    await test_selective_regeneration()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
