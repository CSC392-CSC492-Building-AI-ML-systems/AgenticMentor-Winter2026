from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from src.models.wireframe_spec import WireframeSpec

class MockupAgentRequest(BaseModel):
    """Versioned input contract for Mockup Agent."""
    
    version: str = "1.0"
    
    # Core inputs
    requirements: Dict[str, Any] = Field(
        description="Requirements from RequirementsCollector (functional, user_stories, constraints)"
    )
    
    architecture: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Architecture summary from ProjectArchitect (tech_stack, especially frontend)"
    )
    
    # UI preferences
    platform: str = Field(
        default="web",
        description="Target platform: web, mobile, tablet"
    )
    
    design_preferences: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional hints: layout_style, color_scheme, etc."
    )
    
    # Regeneration support
    existing_spec: Optional[WireframeSpec] = Field(
        default=None,
        description="Previous wireframe spec for selective regeneration"
    )
    
    user_request: Optional[str] = Field(
        default=None,
        description="User's modification request (e.g., 'Add settings screen', 'Change login to use OAuth')"
    )

class MockupAgentResponse(BaseModel):
    """Versioned output contract for Mockup Agent."""
    
    version: str = "1.0"
    
    # Primary outputs
    wireframe_spec: WireframeSpec = Field(
        description="High-level wireframe specification (LLM output)"
    )
    
    excalidraw_json: Dict[str, Any] = Field(
        description="Compiled Excalidraw scene (for embedded canvas)"
    )
    
    # Export artifacts
    export_paths: Optional[Dict[str, str]] = Field(
        default=None,
        description="Paths to exported artifacts: png, svg, json"
    )
    
    # Metadata
    summary: str = Field(
        description="Human-readable summary of mockups generated"
    )
    
    state_delta: Dict[str, Any] = Field(
        description="State updates for ProjectState.mockups"
    )
    
    generation_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent execution metadata: version, timestamp, attempts, etc."
    )

# State update format (for ProjectState.mockups)
class MockupStateEntry(BaseModel):
    """Entry for ProjectState.mockups list."""
    
    screen_name: str
    screen_id: str
    wireframe_spec: Dict[str, Any]  # Serialized ScreenSpec
    excalidraw_scene: Dict[str, Any]  # Full Excalidraw JSON for this screen
    screenshot_path: Optional[str] = None  # PNG export
    user_flow: Optional[str] = None  # Mermaid diagram showing navigation
    interactions: list[str] = Field(default_factory=list)
    template_used: str
    version: str = "1.0"