
from typing import Dict, Tuple

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
# Format: (x_percent, y_percent, width_percent, height_percent)
# All templates must have a "content" region for fallback
TEMPLATES = {
    "auth": TemplateLayout(
        name="auth",
        regions={
            "header": (0, 0, 100, 15),      # Top 15%
            "content": (25, 20, 50, 60),    # Centered: x=25%, y=20%, w=50%, h=60%
            "footer": (0, 85, 100, 15),     # Bottom 15%: y=85% to y=100%
        }
    ),
    "dashboard": TemplateLayout(
        name="dashboard",
        regions={
            "navbar": (0, 0, 100, 8),       # Top navbar: 8% height
            "sidebar": (0, 8, 20, 92),      # Left sidebar: x=0%, y=8%, w=20%, h=92%
            "main": (20, 8, 80, 92),        # Main content: x=20%, y=8%, w=80%, h=92%
            "content": (20, 8, 80, 92),     # Alias for main
        }
    ),
    "list": TemplateLayout(
        name="list",
        regions={
            "navbar": (0, 0, 100, 8),       # Top navbar: 8%
            "filters": (0, 8, 100, 12),     # Search/filter: y=8% to y=20% (12% height)
            "list_content": (0, 20, 100, 80), # List area: y=20% to y=100% (80% height)
            "content": (0, 20, 100, 80),    # Alias for list_content
            "main": (0, 20, 100, 80),       # Alias for main
        }
    ),
    "detail": TemplateLayout(
        name="detail",
        regions={
            "navbar": (0, 0, 100, 8),       # Top navbar: 8%
            "breadcrumb": (0, 8, 100, 5),   # Breadcrumb: y=8% to y=13% (5% height)
            "content": (10, 15, 80, 70),    # Content: y=15% to y=85% (70% height with margins)
            "actions": (10, 90, 80, 10),    # Actions: y=90% to y=100% (10% height with margins)
        }
    ),
    "form": TemplateLayout(
        name="form",
        regions={
            "navbar": (0, 0, 100, 8),       # Top navbar: 8%
            "form_content": (15, 15, 70, 70), # Form: y=15% to y=85% (70% height, centered horizontally)
            "content": (15, 15, 70, 70),    # Alias for form_content
            "actions": (15, 85, 70, 10),    # Actions: y=85% to y=95% (10% height)
        }
    ),
    "blank": TemplateLayout(
        name="blank",
        regions={
            "content": (0, 0, 100, 100),    # Full screen
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