from typing import Any, Dict, Optional
from pathlib import Path
from src.agents.base_agent import BaseAgent
from src.models.mockup_contract import MockupAgentRequest, MockupAgentResponse, MockupStateEntry
from src.models.wireframe_spec import WireframeSpec
from src.tools.excalidraw_compiler import ExcalidrawCompiler
from src.protocols.review_protocol import ReviewResult

class MockupAgent(BaseAgent):
    """Generates UI wireframes as Excalidraw scenes."""
    
    description = "Generates UI wireframes and user flows."
    
    def __init__(
        self,
        state_manager: Any,
        llm_client: Any = None,
        review_config: Optional[dict] = None,
    ) -> None:
        super().__init__(
            name="Mockup Agent",
            llm_client=llm_client,
            review_config=review_config or {"min_score": 0.7},
        )
        self.state_manager = state_manager
        self.compiler = ExcalidrawCompiler()
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for mockup generation."""
        
        # Parse request
        request = MockupAgentRequest(**input_data)
        
        # Generate wireframe spec via LLM
        print("  [1/3] Generating wireframe spec (LLM)...", flush=True)
        wireframe_spec = await self._generate_wireframe_spec(request)
        
        # Compile to Excalidraw JSON
        print("  [2/3] Compiling to Excalidraw scene...", flush=True)
        excalidraw_json = self.compiler.compile(wireframe_spec)
        
        # Optional: Export to PNG/SVG
        print("  [3/3] Exporting artifacts...", flush=True)
        export_paths = await self._export_artifacts(excalidraw_json, wireframe_spec)
        
        # Build response
        response = MockupAgentResponse(
            wireframe_spec=wireframe_spec,
            excalidraw_json=excalidraw_json,
            export_paths=export_paths,
            summary=self._generate_summary(wireframe_spec),
            state_delta=self._build_state_delta(wireframe_spec, excalidraw_json, export_paths),
            generation_metadata={
                "agent": self.name,
                "version": "1.0",
                "timestamp": self.compiler._timestamp(),
            }
        )
        
        return response.model_dump()
    
    async def _generate_wireframe_spec(self, request: MockupAgentRequest) -> WireframeSpec:
        """Generate WireframeSpec via LLM structured output."""
        
        if self.llm_client is None:
            return self._default_wireframe_spec(request)
        
        # Build prompt
        requirements_text = self._format_requirements(request.requirements)
        frontend = request.architecture.get("tech_stack", {}).get("frontend", "Web") if request.architecture else "Web"
        
        prompt = f"""You are a UX Designer. Analyze the requirements and create a wireframe specification for an MVP.

Requirements:
{requirements_text}

Frontend: {frontend}
Platform: {request.platform}

Output a JSON wireframe specification with these fields:
- version: "1.0"
- project_name: string
- platform: "{request.platform}"
- screens: array of screen objects, each with:
  - screen_id: unique slug (e.g., "login", "dashboard")
  - screen_name: human-readable name
  - template: one of "auth", "dashboard", "list", "detail", "form", "blank"
  - components: array of components, each with type, label, optional children, optional metadata
  - notes: optional string
- navigation: array of navigation links with from_screen, to_screen, trigger
- design_notes: optional string

Component types: header, navbar, sidebar, hero, form, table, card_grid, detail_view, footer, tabs, button_group, search_bar

Choose templates based on screen purpose:
- "auth": login/signup screens
- "dashboard": overview with stats and navigation
- "list": browsing/search results
- "detail": single item view
- "form": data entry
- "blank": custom layouts

Order components top-to-bottom as they should appear on screen.
For forms, list field names as children.
For tables, list column names as children.
For card_grid, set metadata.card_count.
For button_group, set metadata.button_count.

Focus on essential MVP screens only (3-5 screens typical).
"""
        
        try:
            response = await self._invoke_llm(prompt)
            text = response.strip()
            
            # Extract JSON from markdown code blocks if present
            text = self._extract_json_from_response(text)
            
            # Parse and validate with Pydantic
            spec = WireframeSpec.model_validate_json(text)
            return spec
        
        except Exception as e:
            print(f"  [mockup] LLM generation failed: {e}, using default spec", flush=True)
            return self._default_wireframe_spec(request)
    
    def _default_wireframe_spec(self, request: MockupAgentRequest) -> WireframeSpec:
        """Fallback wireframe spec."""
        from src.models.wireframe_spec import ScreenSpec, ComponentSpec, NavigationLink
        
        return WireframeSpec(
            version="1.0",
            project_name=request.requirements.get("project_name", "MVP Project"),
            platform=request.platform,
            screens=[
                ScreenSpec(
                    screen_id="home",
                    screen_name="Home",
                    template="blank",
                    components=[
                        ComponentSpec(type="header", label="Home"),
                        ComponentSpec(type="hero", label="Welcome to MVP"),
                    ]
                )
            ],
            navigation=[],
            design_notes="Default placeholder wireframe"
        )
    
    async def _export_artifacts(
        self, excalidraw_json: Dict[str, Any], spec: WireframeSpec
    ) -> Dict[str, str]:
        """Export Excalidraw scene to JSON and PNG."""
        import json
        from pathlib import Path
        
        output_dir = Path("outputs/mockups")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        project_slug = spec.project_name.replace(' ', '_')
        
        # Save JSON file
        json_path = output_dir / f"{project_slug}.excalidraw"
        with open(json_path, "w") as f:
            json.dump(excalidraw_json, f, indent=2)
        
        export_paths = {
            "excalidraw_json": str(json_path),
        }
        
        # Try to export PNG using Playwright
        try:
            png_path = await self._export_to_png(excalidraw_json, output_dir / f"{project_slug}.png")
            if png_path:
                export_paths["png"] = str(png_path)
        except Exception as e:
            print(f"  [mockup] PNG export skipped: {e}", flush=True)
        
        return export_paths
    
    async def _export_to_png(self, excalidraw_json: Dict[str, Any], output_path: Path) -> Optional[Path]:
        """Export Excalidraw scene to PNG using Playwright."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("  [mockup] Playwright not installed. Install with: pip install playwright && playwright install", flush=True)
            return None
        
        try:
            # Create HTML with embedded Excalidraw
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@excalidraw/excalidraw/dist/excalidraw.production.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; overflow: hidden; }}
        #app {{ width: 100vw; height: 100vh; }}
    </style>
</head>
<body>
    <div id="app"></div>
    <script>
        const App = () => {{
            const excalidrawData = {json.dumps(excalidraw_json)};
            return React.createElement(
                ExcalidrawLib.Excalidraw,
                {{
                    initialData: excalidrawData,
                    viewModeEnabled: true,
                    zenModeEnabled: false,
                    gridModeEnabled: true,
                }}
            );
        }};
        
        const root = ReactDOM.createRoot(document.getElementById('app'));
        root.render(React.createElement(App));
        
        // Signal ready after render
        setTimeout(() => {{
            window.excalidrawReady = true;
        }}, 2000);
    </script>
</body>
</html>
"""
            
            import tempfile
            import json as json_module
            
            # Save HTML to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                html_path = f.name
            
            # Calculate viewport size based on content
            # Find max x and y from elements
            max_x = max_y = 0
            for elem in excalidraw_json.get('elements', []):
                elem_x = elem.get('x', 0) + elem.get('width', 0)
                elem_y = elem.get('y', 0) + elem.get('height', 0)
                max_x = max(max_x, elem_x)
                max_y = max(max_y, elem_y)
            
            # Add padding
            viewport_width = int(max_x + 200)
            viewport_height = int(max_y + 200)
            
            # Render with Playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    viewport={'width': viewport_width, 'height': viewport_height}
                )
                
                await page.goto(f'file://{html_path}')
                
                # Wait for Excalidraw to load
                await page.wait_for_function('window.excalidrawReady === true', timeout=10000)
                
                # Take screenshot
                await page.screenshot(path=str(output_path), full_page=True)
                await browser.close()
            
            # Clean up temp file
            import os
            os.unlink(html_path)
            
            print(f"  [mockup] PNG exported to: {output_path}", flush=True)
            return output_path
            
        except Exception as e:
            print(f"  [mockup] PNG export failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_summary(self, spec: WireframeSpec) -> str:
        """Generate human-readable summary."""
        screen_names = [s.screen_name for s in spec.screens]
        return f"Generated {len(spec.screens)} wireframe screens: {', '.join(screen_names)}"
    
    def _build_state_delta(
        self, spec: WireframeSpec, excalidraw_json: Dict[str, Any], export_paths: Dict[str, str]
    ) -> Dict[str, Any]:
        """Build state updates for ProjectState."""
        mockup_entries = []
        
        for screen in spec.screens:
            entry = MockupStateEntry(
                screen_name=screen.screen_name,
                screen_id=screen.screen_id,
                wireframe_spec=screen.model_dump(),
                excalidraw_scene=excalidraw_json,  # For now, store full scene
                screenshot_path=export_paths.get("png"),
                template_used=screen.template,
                interactions=[nav.trigger for nav in spec.navigation if nav.from_screen == screen.screen_id],
            )
            mockup_entries.append(entry.model_dump())
        
        return {
            "mockups": mockup_entries
        }
    
    def _format_requirements(self, requirements: Dict[str, Any]) -> str:
        """Format requirements for prompt."""
        lines = []
        
        if "functional" in requirements:
            lines.append("Functional requirements: " + "; ".join(requirements["functional"]))
        
        if "user_stories" in requirements:
            stories = requirements["user_stories"]
            if stories:
                story_texts = [f"As {s.get('role', 'user')}, I want {s.get('goal', '...')}" for s in stories[:5]]
                lines.append("User stories: " + "; ".join(story_texts))
        
        if "constraints" in requirements:
            lines.append("Constraints: " + "; ".join(requirements["constraints"]))
        
        return "\n".join(lines) if lines else "No specific requirements provided"
    
    def _extract_json_from_response(self, text: str) -> str:
        """Extract JSON from markdown code blocks."""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        return text
    
    async def _invoke_llm(self, prompt: str) -> str:
        """Invoke LLM client."""
        # Simplified - actual implementation depends on your LLM client
        if hasattr(self.llm_client, "ainvoke"):
            response = await self.llm_client.ainvoke(prompt)
            return response.content if hasattr(response, "content") else str(response)
        return ""
    
    # BaseAgent interface
    
    async def _generate(self, input: Any, context: dict, tools: list) -> Dict[str, Any]:
        """BaseAgent interface for execute() compatibility."""
        payload = dict(input) if isinstance(input, dict) else {"prompt": str(input)}
        
        if "requirements" not in payload and context.get("requirements"):
            payload["requirements"] = context["requirements"]
        
        if "architecture" not in payload and context.get("architecture"):
            payload["architecture"] = context["architecture"]
        
        return await self.process(payload)
    
    def _get_quality_criteria(self) -> dict:
        """Quality criteria for review."""
        return {
            "feasibility": 0.4,
            "clarity": 0.3,
            "completeness": 0.3,
        }
    
    async def review(self, artifact: Any, context: Optional[dict] = None) -> ReviewResult:
        """Validate wireframe output."""
        base_result = await super().review(artifact, context or {})
        issues = list(base_result.feedback)
        
        if not isinstance(artifact, dict):
            issues.append("Mockup output must be a dictionary")
            return ReviewResult(is_valid=False, score=0.0, feedback=issues, detailed_scores={})
        
        if "wireframe_spec" not in artifact:
            issues.append("Missing wireframe_spec")
        
        if "excalidraw_json" not in artifact:
            issues.append("Missing excalidraw_json")
        
        wireframe_spec = artifact.get("wireframe_spec", {})
        if not wireframe_spec.get("screens"):
            issues.append("No screens defined in wireframe spec")
        
        score = max(0.0, base_result.score - 0.2 * len(issues))
        
        return ReviewResult(
            is_valid=(score >= 0.7 and not issues),
            score=score,
            feedback=issues,
            detailed_scores=base_result.detailed_scores,
        )