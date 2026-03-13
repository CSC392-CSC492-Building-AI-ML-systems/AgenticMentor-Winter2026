
from typing import Any, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator

_COMPONENT_TYPES = (
    "header", "navbar", "sidebar", "hero", "form", "table", "card_grid",
    "detail_view", "footer", "tabs", "button_group", "search_bar"
)

class ComponentSpec(BaseModel):
    """A single UI component/section within a screen."""
    type: Literal["header", "navbar", "sidebar", "hero", "form", "table", "card_grid",
                  "detail_view", "footer", "tabs", "button_group", "search_bar"]
    label: str = Field(default="Unlabeled", description="Display text or title")
    children: Optional[List[str]] = Field(
        default=None,
        description="Child component labels (e.g., form fields, table columns)"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Extra hints: button_count, column_count, card_count, etc."
    )

    @field_validator("type", mode="before")
    @classmethod
    def coerce_type(cls, v: Any) -> str:
        """Map LLM shorthand (e.g. 'button') to allowed type (e.g. 'button_group')."""
        if not isinstance(v, str):
            return "header"
        s = v.strip().lower()
        if s == "button":
            return "button_group"
        if s in _COMPONENT_TYPES:
            return s
        return "header"

    @field_validator("children", mode="before")
    @classmethod
    def coerce_children_to_strings(cls, v: Any) -> Optional[List[str]]:
        """Accept LLM output where children are objects (e.g. {type, label}) and coerce to list of strings."""
        if v is None:
            return None
        if not isinstance(v, list):
            return None
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                label = item.get("label") or item.get("id") or item.get("type") or str(item)
                result.append(label if isinstance(label, str) else str(label))
            else:
                result.append(str(item))
        return result

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