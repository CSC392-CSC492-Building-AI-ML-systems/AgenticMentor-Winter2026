
from typing import Dict, List, Tuple

class TemplateLayout:
    """Defines component regions for a template."""
    def __init__(
        self,
        name: str,
        regions: Dict[str, Tuple[int, int, int, int]]  # name -> (x, y, width, height) percentages
    ):
        self.name = name
        self.regions = regions  # e.g., {"header": (0, 0, 100, 10), "main": (0, 10, 100, 80)}

# Template definitions (percentages of screen dimensions)
TEMPLATES = {
    "auth": TemplateLayout(
        name="auth",
        regions={
            "header": (0, 0, 100, 15),      # Top 15%
            "content": (25, 20, 50, 60),    # Centered 50% width, 60% height
            "footer": (0, 85, 100, 15),     # Bottom 15%
        }
    ),
    "dashboard": TemplateLayout(
        name="dashboard",
        regions={
            "navbar": (0, 0, 100, 8),       # Top navbar
            "sidebar": (0, 8, 20, 92),      # Left sidebar
            "main": (20, 8, 80, 92),        # Main content area
        }
    ),
    "list": TemplateLayout(
        name="list",
        regions={
            "navbar": (0, 0, 100, 8),
            "filters": (0, 8, 100, 12),     # Search/filter bar
            "list_content": (0, 20, 100, 80),
        }
    ),
    "detail": TemplateLayout(
        name="detail",
        regions={
            "navbar": (0, 0, 100, 8),
            "breadcrumb": (0, 8, 100, 5),
            "content": (10, 15, 80, 75),
            "actions": (10, 90, 80, 10),    # Bottom action buttons
        }
    ),
    "form": TemplateLayout(
        name="form",
        regions={
            "navbar": (0, 0, 100, 8),
            "form_content": (15, 15, 70, 70),
            "actions": (15, 85, 70, 10),
        }
    ),
    "blank": TemplateLayout(
        name="blank",
        regions={
            "content": (0, 0, 100, 100),
        }
    ),
}

# Component type to Excalidraw element mapping
COMPONENT_RENDERERS = {
    "header": "render_header",
    "navbar": "render_navbar",
    "sidebar": "render_sidebar",
    "hero": "render_hero",
    "form": "render_form",
    "table": "render_table",
    "card_grid": "render_card_grid",
    "detail_view": "render_detail_view",
    "footer": "render_footer",
    "tabs": "render_tabs",
    "button_group": "render_button_group",
    "search_bar": "render_search_bar",
}