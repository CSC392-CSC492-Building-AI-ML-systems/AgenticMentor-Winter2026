#!/usr/bin/env python3
"""
Test script for Mockup Agent - Backend only

This script tests the Mockup Agent without LLM (fallback mode) and with LLM if configured.
"""

import asyncio
import json
from pathlib import Path
from src.agents.mockup_agent import MockupAgent
from src.models.mockup_contract import MockupAgentRequest
from src.models.wireframe_spec import WireframeSpec, ScreenSpec, ComponentSpec, NavigationLink


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


async def test_compiler_only():
    """Test 1: Compiler only (no LLM) - Hardcoded WireframeSpec"""
    print_section("TEST 1: Excalidraw Compiler (No LLM)")
    
    from src.tools.excalidraw_compiler import ExcalidrawCompiler
    
    # Create a sample wireframe spec manually
    spec = WireframeSpec(
        version="1.0",
        project_name="Task Manager MVP",
        platform="web",
        screens=[
            ScreenSpec(
                screen_id="login",
                screen_name="Login",
                template="auth",
                components=[
                    ComponentSpec(type="header", label="Task Manager"),
                    ComponentSpec(
                        type="form",
                        label="Sign In",
                        children=["Email", "Password"]
                    ),
                    ComponentSpec(
                        type="button_group",
                        label="Actions",
                        metadata={"button_count": 2}
                    ),
                ],
                notes="Simple login screen"
            ),
            ScreenSpec(
                screen_id="dashboard",
                screen_name="Dashboard",
                template="dashboard",
                components=[
                    ComponentSpec(type="navbar", label="Task Manager"),
                    ComponentSpec(
                        type="sidebar",
                        label="Navigation",
                        children=["Dashboard", "Tasks", "Settings"]
                    ),
                    ComponentSpec(
                        type="card_grid",
                        label="Stats",
                        metadata={"card_count": 3}
                    ),
                    ComponentSpec(
                        type="table",
                        label="Recent Tasks",
                        children=["Title", "Status", "Due Date"]
                    ),
                ],
            ),
            ScreenSpec(
                screen_id="task_form",
                screen_name="Create Task",
                template="form",
                components=[
                    ComponentSpec(type="navbar", label="Task Manager"),
                    ComponentSpec(
                        type="form",
                        label="New Task",
                        children=["Task Title", "Description", "Due Date", "Priority"]
                    ),
                    ComponentSpec(
                        type="button_group",
                        label="Actions",
                        metadata={"button_count": 2}
                    ),
                ],
            ),
        ],
        navigation=[
            NavigationLink(
                from_screen="login",
                to_screen="dashboard",
                trigger="Click Login button"
            ),
            NavigationLink(
                from_screen="dashboard",
                to_screen="task_form",
                trigger="Click New Task"
            ),
        ],
        design_notes="Simple MVP with 3 core screens"
    )
    
    print("✓ WireframeSpec created")
    print(f"  - Project: {spec.project_name}")
    print(f"  - Platform: {spec.platform}")
    print(f"  - Screens: {len(spec.screens)}")
    print(f"  - Navigation links: {len(spec.navigation)}")
    
    # Compile to Excalidraw JSON
    compiler = ExcalidrawCompiler()
    excalidraw_json = compiler.compile(spec)
    
    print("\n✓ Excalidraw JSON compiled")
    print(f"  - Type: {excalidraw_json['type']}")
    print(f"  - Version: {excalidraw_json['version']}")
    print(f"  - Elements: {len(excalidraw_json['elements'])}")
    print(f"  - Grid size: {excalidraw_json['appState']['gridSize']}")
    
    # Save to file
    output_dir = Path("outputs/mockups/test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "test_compiler_only.excalidraw"
    with open(output_file, "w") as f:
        json.dump(excalidraw_json, f, indent=2)
    
    print(f"\n✓ Saved to: {output_file}")
    print(f"  → Open this file at https://excalidraw.com to view the wireframes")
    
    # Show element breakdown
    element_types = {}
    for elem in excalidraw_json['elements']:
        elem_type = elem['type']
        element_types[elem_type] = element_types.get(elem_type, 0) + 1
    
    print("\n  Element breakdown:")
    for elem_type, count in sorted(element_types.items()):
        print(f"    - {elem_type}: {count}")
    
    return excalidraw_json


async def test_agent_fallback_mode():
    """Test 2: MockupAgent without LLM (fallback mode)"""
    print_section("TEST 2: MockupAgent Fallback (No LLM)")
    
    # Create agent without LLM client
    agent = MockupAgent(
        state_manager=None,  # Not needed for this test
        llm_client=None,  # Will trigger fallback
    )
    
    print("✓ MockupAgent initialized (no LLM)")
    
    # Create request
    request = MockupAgentRequest(
        version="1.0",
        requirements={
            "project_name": "E-Commerce Store",
            "functional": [
                "User registration and login",
                "Product browsing and search",
                "Shopping cart management",
                "Checkout process",
            ],
            "user_stories": [
                {"role": "customer", "goal": "browse products easily"},
                {"role": "customer", "goal": "add items to cart"},
                {"role": "customer", "goal": "complete purchase"},
            ],
            "constraints": ["Mobile-friendly", "Fast loading"],
        },
        architecture={
            "tech_stack": {
                "frontend": "React + TypeScript",
                "backend": "Node.js + Express",
                "database": "PostgreSQL",
            }
        },
        platform="web",
    )
    
    print("\n✓ Request created")
    print(f"  - Project: {request.requirements['project_name']}")
    print(f"  - Frontend: {request.architecture['tech_stack']['frontend']}")
    print(f"  - Platform: {request.platform}")
    
    # Process request
    print("\n⏳ Processing (using fallback spec since no LLM)...")
    response = await agent.process(request.model_dump())
    
    print("\n✓ Response generated")
    print(f"  - Summary: {response['summary']}")
    print(f"  - Wireframe version: {response['wireframe_spec']['version']}")
    print(f"  - Screens generated: {len(response['wireframe_spec']['screens'])}")
    print(f"  - Excalidraw elements: {len(response['excalidraw_json']['elements'])}")
    
    # Show exported files
    if response.get('export_paths'):
        print("\n  Exported files:")
        for key, path in response['export_paths'].items():
            print(f"    - {key}: {path}")
    
    # Show state delta
    mockup_entries = response['state_delta']['mockups']
    print(f"\n  State delta contains {len(mockup_entries)} mockup entries")
    for entry in mockup_entries:
        print(f"    - {entry['screen_name']} (template: {entry['template_used']})")
    
    return response


async def test_agent_with_llm():
    """Test 3: MockupAgent with LLM (if configured)"""
    print_section("TEST 3: MockupAgent with LLM")
    
    from src.utils.config import settings
    
    # Check if LLM is configured
    if not settings.google_api_key or settings.google_api_key == "your-gemini-api-key-here":
        print("⚠️  GOOGLE_API_KEY not configured in .env")
        print("   Skipping LLM test. To enable:")
        print("   1. Copy .env.example to .env")
        print("   2. Add your Google API key: GOOGLE_API_KEY=your-key-here")
        print("   3. Run this test again")
        return None
    
    print("✓ LLM configured (Google Gemini)")
    
    # Initialize LLM client (similar to ProjectArchitect)
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    llm_client = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=settings.google_api_key,
        temperature=0.7,
    )
    
    print("✓ LLM client initialized")
    
    # Create agent with LLM
    agent = MockupAgent(
        state_manager=None,
        llm_client=llm_client,
    )
    
    # Create request
    request = MockupAgentRequest(
        version="1.0",
        requirements={
            "project_name": "Fitness Tracker",
            "functional": [
                "User authentication",
                "Track workouts and exercises",
                "View progress over time",
                "Set fitness goals",
            ],
            "user_stories": [
                {"role": "user", "goal": "log my daily workouts"},
                {"role": "user", "goal": "see my progress charts"},
                {"role": "user", "goal": "set and track fitness goals"},
            ],
            "constraints": ["Mobile-first design", "Simple and intuitive"],
        },
        architecture={
            "tech_stack": {
                "frontend": "React Native",
                "backend": "Python + FastAPI",
                "database": "MongoDB",
            }
        },
        platform="mobile",
    )
    
    print("\n✓ Request created")
    print(f"  - Project: {request.requirements['project_name']}")
    print(f"  - Frontend: {request.architecture['tech_stack']['frontend']}")
    print(f"  - Platform: {request.platform}")
    
    # Process request
    print("\n⏳ Processing (LLM will generate wireframe spec)...")
    try:
        response = await agent.process(request.model_dump())
        
        print("\n✓ Response generated by LLM")
        print(f"  - Summary: {response['summary']}")
        print(f"  - Wireframe version: {response['wireframe_spec']['version']}")
        print(f"  - Screens generated: {len(response['wireframe_spec']['screens'])}")
        print(f"  - Navigation links: {len(response['wireframe_spec']['navigation'])}")
        
        # Show screen details
        print("\n  Screens:")
        for screen in response['wireframe_spec']['screens']:
            print(f"    - {screen['screen_name']} ({screen['screen_id']})")
            print(f"      Template: {screen['template']}")
            print(f"      Components: {len(screen['components'])}")
            for comp in screen['components']:
                children_info = f" [{', '.join(comp['children'])}]" if comp.get('children') else ""
                print(f"        • {comp['type']}: {comp['label']}{children_info}")
        
        # Show navigation
        if response['wireframe_spec']['navigation']:
            print("\n  Navigation:")
            for nav in response['wireframe_spec']['navigation']:
                print(f"    - {nav['from_screen']} → {nav['to_screen']}: {nav['trigger']}")
        
        # Show exported files
        if response.get('export_paths'):
            print("\n  Exported files:")
            for key, path in response['export_paths'].items():
                print(f"    - {key}: {path}")
        
        return response
        
    except Exception as e:
        print(f"\n❌ LLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_review_validation():
    """Test 4: Review and validation"""
    print_section("TEST 4: Review & Validation")
    
    agent = MockupAgent(state_manager=None, llm_client=None)
    
    # Test valid artifact
    valid_artifact = {
        "wireframe_spec": {
            "version": "1.0",
            "project_name": "Test",
            "platform": "web",
            "screens": [
                {
                    "screen_id": "home",
                    "screen_name": "Home",
                    "template": "blank",
                    "components": [{"type": "header", "label": "Test"}],
                }
            ],
            "navigation": [],
        },
        "excalidraw_json": {"type": "excalidraw", "version": 2, "elements": []},
        "summary": "Test mockup",
        "state_delta": {"mockups": []},
    }
    
    print("✓ Testing valid artifact...")
    result = await agent.review(valid_artifact)
    print(f"  - Valid: {result.is_valid}")
    print(f"  - Score: {result.score:.2f}")
    print(f"  - Issues: {result.feedback if result.feedback else 'None'}")
    
    # Test invalid artifact (missing wireframe_spec)
    invalid_artifact = {
        "excalidraw_json": {"type": "excalidraw"},
        "summary": "Test",
        "state_delta": {},
    }
    
    print("\n✓ Testing invalid artifact (missing wireframe_spec)...")
    result = await agent.review(invalid_artifact)
    print(f"  - Valid: {result.is_valid}")
    print(f"  - Score: {result.score:.2f}")
    print(f"  - Issues: {result.feedback}")
    
    # Test invalid artifact (no screens)
    no_screens_artifact = {
        "wireframe_spec": {
            "version": "1.0",
            "project_name": "Test",
            "platform": "web",
            "screens": [],  # Empty!
            "navigation": [],
        },
        "excalidraw_json": {"type": "excalidraw"},
        "summary": "Test",
        "state_delta": {},
    }
    
    print("\n✓ Testing invalid artifact (no screens)...")
    result = await agent.review(no_screens_artifact)
    print(f"  - Valid: {result.is_valid}")
    print(f"  - Score: {result.score:.2f}")
    print(f"  - Issues: {result.feedback}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  MOCKUP AGENT TEST SUITE - BACKEND ONLY")
    print("=" * 80)
    
    try:
        # Test 1: Compiler only
        await test_compiler_only()
        
        # Test 2: Agent fallback mode
        await test_agent_fallback_mode()
        
        # Test 3: Agent with LLM (if configured)
        await test_agent_with_llm()
        
        # Test 4: Review validation
        await test_review_validation()
        
        print_section("✅ ALL TESTS COMPLETED")
        
        print("\n📋 NEXT STEPS:")
        print("  1. Check outputs/mockups/test/ for generated .excalidraw files")
        print("  2. Open files at https://excalidraw.com to view wireframes")
        print("  3. To test with LLM: Configure GOOGLE_API_KEY in .env")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
