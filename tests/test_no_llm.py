#!/usr/bin/env python3
"""
Test Mockup Agent WITHOUT LLM

This script runs only the non-LLM tests (Tests 1, 2, and 4).
Perfect for testing the core functionality without API keys.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import json
from src.agents.mockup_agent import MockupAgent
from src.models.mockup_contract import MockupAgentRequest
from src.models.wireframe_spec import WireframeSpec, ScreenSpec, ComponentSpec, NavigationLink
from src.tools.excalidraw_compiler import ExcalidrawCompiler


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def _create_preview_html(excalidraw_json: dict, html_path: Path) -> None:
    """Create HTML preview file and open in browser."""
    import webbrowser
    import base64
    import zlib
    
    # Encode excalidraw JSON for URL
    json_str = json.dumps(excalidraw_json)
    compressed = zlib.compress(json_str.encode('utf-8'), level=9)
    encoded = base64.urlsafe_b64encode(compressed).decode('utf-8')
    excalidraw_url = f"https://excalidraw.com/#json={encoded}"
    
    json_path = html_path.with_suffix('.excalidraw')
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Mockup Preview - {html_path.stem}</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            margin: 0 0 10px 0;
            color: #333;
            font-size: 28px;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 30px;
            font-size: 16px;
        }}
        .button-group {{
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
        }}
        .btn {{
            padding: 12px 24px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 16px;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
            display: inline-block;
        }}
        .btn-primary {{
            background: #3b82f6;
            color: white;
        }}
        .btn-primary:hover {{
            background: #2563eb;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }}
        .info-box {{
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        }}
        .info-box h3 {{
            margin: 0 0 8px 0;
            color: #1e40af;
            font-size: 16px;
        }}
        .info-box p {{
            margin: 0;
            color: #1e40af;
            line-height: 1.5;
        }}
        code {{
            color: #60a5fa;
            font-family: 'Monaco', monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 {html_path.stem}</h1>
        <p class="subtitle">UI Wireframe Mockup</p>
        
        <div class="info-box">
            <h3>✨ Your mockup is ready!</h3>
            <p>Click the button below to open and edit your wireframe in Excalidraw.</p>
        </div>
        
        <div class="button-group">
            <a href="{excalidraw_url}" target="_blank" class="btn btn-primary">
                🚀 Open in Excalidraw Editor
            </a>
        </div>
        
        <div class="info-box">
            <h3>📁 Files Generated</h3>
            <p><strong>JSON File:</strong> <code>{json_path.name}</code></p>
            <p><strong>Elements:</strong> {len(excalidraw_json.get('elements', []))}</p>
        </div>
    </div>
</body>
</html>"""
    
    with open(html_path, 'w') as f:
        f.write(html_content)
    
    # Convert to absolute path
    html_path_abs = html_path.resolve()
    print(f"✓ Preview HTML created: {html_path_abs}")
    
    try:
        webbrowser.open(f'file://{html_path_abs}')
        print(f"✓ Opening in browser...")
    except Exception as e:
        print(f"⚠ Could not auto-open: {e}")
        print(f"  → Open manually: file://{html_path_abs}")



async def test_compiler_only():
    """Test 1: Compiler only (no LLM) - Hardcoded WireframeSpec"""
    print_section("TEST 1: Excalidraw Compiler (No LLM)")
    
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
                ],
            ),
        ],
        navigation=[
            NavigationLink(
                from_screen="login",
                to_screen="dashboard",
                trigger="Click Login button"
            ),
        ],
    )
    
    print("✓ WireframeSpec created")
    print(f"  - Screens: {len(spec.screens)}")
    
    # Compile to Excalidraw JSON
    compiler = ExcalidrawCompiler()
    excalidraw_json = compiler.compile(spec)
    
    print(f"✓ Compiled to Excalidraw JSON ({len(excalidraw_json['elements'])} elements)")
    
    # Save
    output_dir = Path("outputs/mockups/test")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "no_llm_test.excalidraw"
    
    with open(output_file, "w") as f:
        json.dump(excalidraw_json, f, indent=2)
    
    print(f"✓ Saved: {output_file}")
    
    # Create HTML preview and auto-open
    html_file = output_file.with_suffix('.html')
    _create_preview_html(excalidraw_json, html_file)
    
    return excalidraw_json


async def test_agent_fallback():
    """Test 2: MockupAgent without LLM (fallback mode)"""
    print_section("TEST 2: MockupAgent Fallback (No LLM)")
    
    agent = MockupAgent(state_manager=None, llm_client=None)
    print("✓ Agent initialized (no LLM)")
    
    request = MockupAgentRequest(
        requirements={
            "project_name": "Simple App",
            "functional": ["User management", "Data display"],
        },
        platform="web",
    )
    
    print("✓ Processing...")
    response = await agent.process(request.model_dump())
    
    print(f"✓ Generated: {response['summary']}")
    
    if response.get('export_paths'):
        for key, path in response['export_paths'].items():
            print(f"  - {key}: {path}")
            if key == "png":
                from pathlib import Path
                if Path(path).exists():
                    size = Path(path).stat().st_size
                    print(f"    PNG created: {size:,} bytes")
    
    return response


async def test_validation():
    """Test 3: Validation"""
    print_section("TEST 3: Review & Validation")
    
    agent = MockupAgent(state_manager=None, llm_client=None)
    
    valid_artifact = {
        "wireframe_spec": {
            "version": "1.0",
            "project_name": "Test",
            "platform": "web",
            "screens": [{"screen_id": "home", "screen_name": "Home", "template": "blank", "components": []}],
            "navigation": [],
        },
        "excalidraw_json": {"type": "excalidraw", "version": 2, "elements": []},
        "summary": "Test",
        "state_delta": {"mockups": []},
    }
    
    result = await agent.review(valid_artifact)
    print(f"✓ Validation works (score: {result.score:.2f})")


async def test_standard_mockup():
    """Test 4: Standard Mockup with Typical LLM Output"""
    print_section("TEST 4: Standard Mockup (Real-world Example)")
    
    agent = MockupAgent(state_manager=None, llm_client=None)
    print("✓ Agent initialized")
    
    # Create a realistic mockup request like an LLM would generate
    request = MockupAgentRequest(
        requirements={
            "project_name": "FitTrack MVP",
            "functional": [
                "User authentication",
                "Track workouts",
                "View progress dashboard",
                "Set fitness goals"
            ],
            "user_stories": [
                {"role": "user", "goal": "log my daily workouts", "benefit": "track my fitness progress"},
                {"role": "user", "goal": "see my progress charts", "benefit": "stay motivated"},
                {"role": "user", "goal": "set fitness goals", "benefit": "have clear targets"}
            ]
        },
        architecture={
            "tech_stack": {
                "frontend": "React",
                "backend": "Node.js",
                "database": "PostgreSQL"
            }
        },
        platform="web",
    )
    
    print("✓ Request created")
    print(f"  - Project: {request.requirements['project_name']}")
    print(f"  - Features: {len(request.requirements['functional'])}")
    
    # Process (will use fallback since no LLM)
    print("\n⏳ Processing mockup...")
    response = await agent.process(request.model_dump())
    
    print(f"\n✓ Mockup generated")
    print(f"  - Summary: {response['summary']}")
    print(f"  - Elements: {len(response['excalidraw_json']['elements'])}")
    
    if response.get('export_paths'):
        print(f"\n  Files created:")
        for key, path in response['export_paths'].items():
            print(f"    - {key}: {path}")
            
            # Check if HTML file exists and has content
            if key == "preview_html":
                from pathlib import Path
                html_file = Path(path)
                if html_file.exists():
                    size = html_file.stat().st_size
                    print(f"      ✓ HTML preview: {size:,} bytes")
                    print(f"      → Open in browser to test rendering")
    
    return response


async def main():
    print("\n" + "=" * 80)
    print("  MOCKUP AGENT TEST - NO LLM REQUIRED")
    print("=" * 80)
    
    try:
        await test_compiler_only()
        await test_agent_fallback()
        await test_validation()
        await test_standard_mockup()
        
        print_section("✅ ALL TESTS PASSED")
        print("📋 Files generated:")
        print("   - .excalidraw: JSON files (open at https://excalidraw.com)")
        print("   - .html: Interactive previews (auto-opened in browser)")
        print("📋 Check: outputs/mockups/ directory")
        print()
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
