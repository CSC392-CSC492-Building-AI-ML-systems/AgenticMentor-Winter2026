#!/usr/bin/env python3
"""
Test Mockup Agent with ChatGPT-style Conversational AI App
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from src.agents.mockup_agent import MockupAgent
from src.models.mockup_contract import MockupAgentRequest


async def test_chat_ai_app():
    """Test with a ChatGPT-style AI Chat App"""
    print("\n" + "=" * 80)
    print("  TESTING: Conversational AI Chat App (ChatGPT-style)")
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
            model="gemini-flash-latest",  # Updated model name
            api_key=settings.gemini_api_key,
            temperature=0.7,
        )
    
    agent = MockupAgent(state_manager=None, llm_client=llm_client)
    
    # Create request for AI Chat App
    request = MockupAgentRequest(
        version="1.0",
        requirements={
            "project_name": "ConvoAI",
            "functional": [
                "Real-time chat interface with AI assistant",
                "Conversation history and threading",
                "Code block rendering with syntax highlighting",
                "Copy and share responses",
                "New chat and conversation management",
                "Dark mode and light mode toggle",
                "Markdown and rich text rendering",
                "Model selection (GPT-4, GPT-3.5, Claude)",
                "Prompt templates and suggestions",
                "File upload for context",
            ],
            "user_stories": [
                {"role": "developer", "goal": "get coding help with syntax highlighting"},
                {"role": "writer", "goal": "brainstorm and iterate on creative content"},
                {"role": "student", "goal": "ask questions and learn interactively"},
                {"role": "power user", "goal": "switch between AI models for different tasks"},
                {"role": "user", "goal": "access my previous conversations easily"},
            ],
            "constraints": [
                "Web and mobile responsive",
                "Fast response streaming",
                "Clean, minimal interface like ChatGPT",
                "Keyboard shortcuts for power users",
            ],
        },
        architecture={
            "tech_stack": {
                "frontend": "React + TypeScript + Tailwind",
                "backend": "Python + FastAPI",
                "database": "PostgreSQL + Redis",
            }
        },
        platform="web",
    )
    
    print("📋 Request created:")
    print(f"  - Project: {request.requirements['project_name']}")
    print(f"  - Platform: {request.platform}")
    print(f"  - Features: {len(request.requirements['functional'])}")
    print(f"  - User stories: {len(request.requirements['user_stories'])}")
    
    # Process
    print("\n⏳ Processing (this may take 10-20 seconds with LLM)...")
    try:
        response = await agent.process(request.model_dump())
        
        print("\n✅ SUCCESS!")
        print(f"  - Summary: {response['summary']}")
        print(f"  - Total screens: {len(response['wireframe_spec']['screens'])}")
        print(f"  - Navigation links: {len(response['wireframe_spec']['navigation'])}")
        print(f"  - Excalidraw elements: {len(response['excalidraw_json']['elements'])}")
        
        # Show screens in detail
        print("\n💬 Screens Generated:")
        for idx, screen in enumerate(response['wireframe_spec']['screens'], 1):
            print(f"\n  {idx}. {screen['screen_name']} (ID: {screen['screen_id']})")
            print(f"     Template: {screen['template']}")
            print(f"     Components ({len(screen['components'])}):")
            for comp in screen['components']:
                children_preview = ""
                if comp.get('children'):
                    children_list = comp['children'][:3]
                    if len(comp['children']) > 3:
                        children_preview = f" [{', '.join(children_list)}, +{len(comp['children'])-3} more]"
                    else:
                        children_preview = f" [{', '.join(children_list)}]"
                
                metadata_preview = ""
                if comp.get('metadata'):
                    metadata_preview = f" (metadata: {comp['metadata']})"
                
                print(f"       • {comp['type']}: {comp['label']}{children_preview}{metadata_preview}")
            
            if screen.get('notes'):
                print(f"     Notes: {screen['notes']}")
        
        # Show navigation flow
        if response['wireframe_spec']['navigation']:
            print("\n🔗 Navigation Flow:")
            for nav in response['wireframe_spec']['navigation']:
                print(f"  {nav['from_screen']} → {nav['to_screen']}")
                print(f"    Trigger: {nav['trigger']}")
        
        # Show design notes
        if response['wireframe_spec'].get('design_notes'):
            print(f"\n📝 Design Notes:")
            print(f"  {response['wireframe_spec']['design_notes']}")
        
        # Show exports
        print("\n📁 Exported Files:")
        if response.get('export_paths'):
            for key, path in response['export_paths'].items():
                print(f"  - {key}: {path}")
                if key == "png":
                    from pathlib import Path
                    if Path(path).exists():
                        size = Path(path).stat().st_size
                        print(f"    ✓ PNG created: {size:,} bytes")
                    else:
                        print(f"    ⚠️ PNG not found (may have timed out)")
        
        # Show state delta
        mockup_entries = response['state_delta']['mockups']
        print(f"\n📊 State Delta: {len(mockup_entries)} mockup entries")
        
        print("\n" + "=" * 80)
        print("✅ ChatGPT-Style App Test Complete!")
        print("=" * 80)
        print("\n📋 Next steps:")
        print("  1. Open: outputs/mockups/ConvoAI.excalidraw at https://excalidraw.com")
        print("  2. View wireframes showing chat interface, sidebars, settings")
        print("  3. Check navigation flow between screens")
        print("\n")
        
        return response
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(test_chat_ai_app())
