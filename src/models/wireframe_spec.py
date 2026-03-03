
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class ComponentSpec(BaseModel):
    """A single UI component/section within a screen."""
    type: Literal[
        "header", "navbar", "sidebar", "hero", "form", "table", "card_grid",
        "detail_view", "footer", "tabs", "button_group", "search_bar"
    ]
    label: str = Field(description="Display text or title")
    children: Optional[List[str]] = Field(
        default=None,
        description="Child component labels (e.g., form fields, table columns)"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Extra hints: button_count, column_count, card_count, etc."
    )

class NavigationLink(BaseModel):
    """Navigation between screens."""
    from_screen: str
    to_screen: str
    trigger: str = Field(description="e.g., 'Click Login button', 'Submit form'")

class ScreenSpec(BaseModel):
    """A single screen/page in the wireframe."""
    screen_id: str = Field(description="Unique identifier, e.g., 'login', 'dashboard'")
    screen_name: str = Field(description="Human-readable name")
    template: Literal["auth", "dashboard", "list", "detail", "form", "blank"]
    components: List[ComponentSpec] = Field(
        description="Ordered list of components from top to bottom"
    )
    notes: Optional[str] = None

class WireframeSpec(BaseModel):
    """Complete wireframe specification output by LLM."""
    version: str = "1.0"
    project_name: str
    platform: Literal["web", "mobile", "tablet"] = "web"
    screens: List[ScreenSpec]
    navigation: List[NavigationLink]
    design_notes: Optional[str] = None