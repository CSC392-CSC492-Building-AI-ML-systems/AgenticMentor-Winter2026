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
        
        # Export artifacts and auto-preview
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
        """Intelligent fallback wireframe spec based on requirements."""
        from src.models.wireframe_spec import ScreenSpec, ComponentSpec, NavigationLink
        
        project_name = request.requirements.get("project_name", "MVP Project")
        functional_reqs = request.requirements.get("functional", [])
        
        screens = []
        navigation = []
        
        # Always start with login screen
        screens.append(ScreenSpec(
            screen_id="login",
            screen_name="Login",
            template="auth",
            components=[
                ComponentSpec(type="header", label=f"{project_name}"),
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
            ]
        ))
        
        # Add dashboard screen
        screens.append(ScreenSpec(
            screen_id="dashboard",
            screen_name="Dashboard",
            template="dashboard",
            components=[
                ComponentSpec(type="navbar", label=f"{project_name}"),
                ComponentSpec(
                    type="sidebar",
                    label="Navigation",
                    children=["Dashboard"] + functional_reqs[:3] + ["Settings"]
                ),
                ComponentSpec(
                    type="card_grid",
                    label="Overview Stats",
                    metadata={"card_count": min(4, len(functional_reqs) + 1)}
                ),
                ComponentSpec(
                    type="table",
                    label="Recent Activity",
                    children=["Date", "Action", "Status"]
                ),
            ]
        ))
        
        # Generate screens based on functional requirements
        for idx, feature in enumerate(functional_reqs[:3]):  # Limit to 3 feature screens
            feature_slug = feature.lower().replace(" ", "_")[:20]
            
            # Determine template based on keywords
            if any(keyword in feature.lower() for keyword in ["track", "view", "list", "browse"]):
                template = "list"
                components = [
                    ComponentSpec(type="navbar", label=f"{project_name}"),
                    ComponentSpec(type="search_bar", label="Search"),
                    ComponentSpec(
                        type="table",
                        label=feature,
                        children=["Name", "Date", "Status", "Actions"]
                    ),
                ]
            elif any(keyword in feature.lower() for keyword in ["create", "add", "new", "edit", "set"]):
                template = "form"
                components = [
                    ComponentSpec(type="navbar", label=f"{project_name}"),
                    ComponentSpec(
                        type="form",
                        label=feature,
                        children=["Title", "Description", "Date", "Category"]
                    ),
                    ComponentSpec(
                        type="button_group",
                        label="Actions",
                        metadata={"button_count": 2}
                    ),
                ]
            else:
                template = "detail"
                components = [
                    ComponentSpec(type="navbar", label=f"{project_name}"),
                    ComponentSpec(
                        type="detail_view",
                        label=feature,
                        children=["Name", "Description", "Status", "Created"]
                    ),
                ]
            
            screens.append(ScreenSpec(
                screen_id=f"{feature_slug}_{idx}",
                screen_name=feature,
                template=template,
                components=components
            ))
        
        # Create navigation flow
        navigation.append(NavigationLink(
            from_screen="login",
            to_screen="dashboard",
            trigger="Click Login button"
        ))
        
        for idx, feature in enumerate(functional_reqs[:3]):
            feature_slug = feature.lower().replace(" ", "_")[:20]
            navigation.append(NavigationLink(
                from_screen="dashboard",
                to_screen=f"{feature_slug}_{idx}",
                trigger=f"Click {feature}"
            ))
        
        return WireframeSpec(
            version="1.0",
            project_name=project_name,
            platform=request.platform,
            screens=screens,
            navigation=navigation,
            design_notes=f"Generated {len(screens)} screens based on {len(functional_reqs)} functional requirements"
        )
    
    async def _export_artifacts(
        self, excalidraw_json: Dict[str, Any], spec: WireframeSpec
    ) -> Dict[str, str]:
        """Export Excalidraw scene to JSON and auto-preview in browser."""
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
        
        # Auto-preview in browser
        print("  [3.1/3] Opening preview in browser...", flush=True)
        preview_info = await self._auto_preview(excalidraw_json, json_path)
        export_paths.update(preview_info)
        
        return export_paths
    
    async def _auto_preview(
        self, 
        excalidraw_json: Dict[str, Any], 
        json_path: Path
    ) -> Dict[str, str]:
        """Auto-preview the mockup in browser."""
        import webbrowser
        import json
        
        preview_info = {}
        
        # Create local HTML preview (editable)
        html_path = json_path.with_suffix('.html')
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mockup Preview - {json_path.stem}</title>
    <script crossorigin src="https://unpkg.com/react@18.2.0/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18.2.0/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@excalidraw/excalidraw@0.17.6/dist/excalidraw.production.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        #app {{ width: 100vw; height: 100vh; }}
        .toolbar {{
            position: fixed;
            top: 60px;
            right: 20px;
            z-index: 999999;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .btn {{
            padding: 12px 20px;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
            transition: all 0.2s;
            font-size: 14px;
            white-space: nowrap;
        }}
        .btn:hover {{
            background: #2563eb;
            transform: translateX(-2px);
            box-shadow: 0 6px 16px rgba(59, 130, 246, 0.5);
        }}
        .btn-secondary {{
            background: #64748b;
            box-shadow: 0 4px 12px rgba(100, 116, 139, 0.4);
        }}
        .btn-secondary:hover {{
            background: #475569;
            box-shadow: 0 6px 16px rgba(100, 116, 139, 0.5);
        }}
    </style>
</head>
<body>
    <div class="toolbar">
        <button class="btn" onclick="downloadJSON()">💾 Download JSON</button>
        <button class="btn btn-secondary" onclick="exportPNG()">🖼️ Export PNG</button>
    </div>
    <div id="app"></div>
    
    <script>
        const initialData = {json.dumps(excalidraw_json)};
        let excalidrawAPI = null;
        
        function initExcalidraw() {{
            if (typeof React === 'undefined' || 
                typeof ReactDOM === 'undefined' || 
                typeof ExcalidrawLib === 'undefined') {{
                setTimeout(initExcalidraw, 100);
                return;
            }}
            
            const {{ Excalidraw, exportToBlob }} = ExcalidrawLib;
            
            const App = () => {{
                const [excalidrawAPI, setExcalidrawAPI] = React.useState(null);
                
                // Store API globally when available
                React.useEffect(() => {{
                    if (excalidrawAPI) {{
                        window.excalidrawAPI = excalidrawAPI;
                    }}
                }}, [excalidrawAPI]);
                
                return React.createElement(Excalidraw, {{
                    initialData: initialData,
                    ref: setExcalidrawAPI
                }});
            }};
            
            const root = ReactDOM.createRoot(document.getElementById('app'));
            root.render(React.createElement(App));
        }}
        
        function downloadJSON() {{
            if (!window.excalidrawAPI) {{
                alert('Excalidraw not ready yet. Please wait a moment and try again.');
                return;
            }}
            
            const elements = window.excalidrawAPI.getSceneElements();
            const appState = window.excalidrawAPI.getAppState();
            const files = window.excalidrawAPI.getFiles();
            
            const data = {{
                type: 'excalidraw',
                version: 2,
                source: 'https://excalidraw.com',
                elements: elements,
                appState: {{
                    gridSize: appState.gridSize,
                    viewBackgroundColor: appState.viewBackgroundColor
                }},
                files: files
            }};
            
            const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '{json_path.stem}.excalidraw';
            a.click();
            URL.revokeObjectURL(url);
        }}
        
        function exportPNG() {{
            if (!window.excalidrawAPI) {{
                alert('Excalidraw not ready yet. Please wait a moment and try again.');
                return;
            }}
            
            const elements = window.excalidrawAPI.getSceneElements();
            const appState = window.excalidrawAPI.getAppState();
            const files = window.excalidrawAPI.getFiles();
            
            if (ExcalidrawLib.exportToBlob) {{
                ExcalidrawLib.exportToBlob({{
                    elements: elements,
                    appState: appState,
                    files: files,
                    mimeType: 'image/png'
                }}).then(blob => {{
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = '{json_path.stem}.png';
                    a.click();
                    URL.revokeObjectURL(url);
                }}).catch(err => {{
                    console.error('Export failed:', err);
                    alert('Export failed. Check console for details.');
                }});
            }} else {{
                alert('Export function not available in this Excalidraw version');
            }}
        }}
        
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', initExcalidraw);
        }} else {{
            initExcalidraw();
        }}
    </script>
</body>
</html>"""
        
        with open(html_path, 'w') as f:
            f.write(html_content)
        
        # Convert to absolute path
        html_path_abs = html_path.resolve()
        preview_info["preview_html"] = str(html_path_abs)
        
        # Auto-open in browser
        try:
            webbrowser.open(f'file://{html_path_abs}')
            print(f"  ✓ Preview opened in browser: {html_path.name}", flush=True)
        except Exception as e:
            print(f"  ⚠ Could not auto-open browser: {e}", flush=True)
            print(f"  → Open manually: file://{html_path_abs}", flush=True)
        
        return preview_info
    
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
                excalidraw_scene=excalidraw_json,
                screenshot_path=export_paths.get("preview_html"),  # Store HTML preview path
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