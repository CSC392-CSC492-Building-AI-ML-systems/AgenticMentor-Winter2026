#!/usr/bin/env python3
"""
Quick test with different project - Recipe Sharing App
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from src.agents.mockup_agent import MockupAgent
from src.models.mockup_contract import MockupAgentRequest


async def test_recipe_app():
    """Test with a Recipe Sharing App"""
    print("\n" + "=" * 80)
    print("  TESTING: Recipe Sharing App")
    print("=" * 80 + "\n")
    
    # Initialize with LLM
    from src.utils.config import settings
    
    if not settings.gemini_api_key or settings.gemini_api_key == "your-gemini-api-key-here":
        print("⚠️  GEMINI_API_KEY not configured - using fallback mode")
        llm_client = None
    else:
        print("✓ Using LLM (Gemini)")
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm_client = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            api_key=settings.gemini_api_key,
            temperature=0.7,
        )
    
    agent = MockupAgent(state_manager=None, llm_client=llm_client)
    
    # Create request for Recipe App
    request = MockupAgentRequest(
        version="1.0",
        requirements={
            "project_name": "FoodieShare",
            "functional": [
                "Browse recipe feed with photos",
                "Search recipes by ingredients or name",
                "View detailed recipe with steps and ingredients",
                "Save favorite recipes",
                "Share your own recipes with photos",
                "Rate and comment on recipes",
            ],
            "user_stories": [
                {"role": "home cook", "goal": "find recipes using ingredients I have"},
                {"role": "food blogger", "goal": "share my recipes with the community"},
                {"role": "beginner", "goal": "follow step-by-step cooking instructions"},
            ],
            "constraints": ["Mobile-first", "Photo-heavy design", "Simple navigation"],
        },
        architecture={
            "tech_stack": {
                "frontend": "Next.js + React",
                "backend": "Node.js + Express",
                "database": "MongoDB",
            }
        },
        platform="mobile",
    )
    
    print("📋 Request created:")
    print(f"  - Project: {request.requirements['project_name']}")
    print(f"  - Platform: {request.platform}")
    print(f"  - Features: {len(request.requirements['functional'])}")
    
    # Process
    print("\n⏳ Processing...")
    try:
        response = await agent.process(request.model_dump())
        
        print("\n✅ Success!")
        print(f"  - Summary: {response['summary']}")
        print(f"  - Screens: {len(response['wireframe_spec']['screens'])}")
        print(f"  - Navigation: {len(response['wireframe_spec']['navigation'])} links")
        
        # Show screens
        print("\n📱 Screens Generated:")
        for screen in response['wireframe_spec']['screens']:
            print(f"  - {screen['screen_name']} ({screen['screen_id']})")
            print(f"    Template: {screen['template']}")
            print(f"    Components: {len(screen['components'])}")
            for comp in screen['components'][:3]:  # Show first 3 components
                children = f" [{', '.join(comp.get('children', [])[:3])}]" if comp.get('children') else ""
                print(f"      • {comp['type']}: {comp['label']}{children}")
            if len(screen['components']) > 3:
                print(f"      • ... and {len(screen['components']) - 3} more")
        
        # Show navigation
        if response['wireframe_spec']['navigation']:
            print("\n🔗 Navigation:")
            for nav in response['wireframe_spec']['navigation']:
                print(f"  - {nav['from_screen']} → {nav['to_screen']}")
        
        # Show exports
        if response.get('export_paths'):
            print("\n📁 Exported files:")
            for key, path in response['export_paths'].items():
                print(f"  - {key}: {path}")
                if key == "png":
                    from pathlib import Path
                    if Path(path).exists():
                        size = Path(path).stat().st_size
                        print(f"    ✓ PNG created: {size:,} bytes")
        
        print("\n" + "=" * 80)
        print("✅ Recipe App Test Complete!")
        print("=" * 80)
        print("\n📋 Next steps:")
        print("  1. Open .excalidraw file at https://excalidraw.com")
        print("  2. View PNG if generated")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_recipe_app())
