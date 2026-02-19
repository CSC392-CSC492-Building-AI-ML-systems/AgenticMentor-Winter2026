
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
            "header":       (0,  0,  100, 12),   # Top bar
            "content":      (20, 13, 60,  58),   # Centered form card
            "form_content": (20, 13, 60,  58),   # Alias
            "actions":      (20, 73, 60,  10),   # Buttons — below form, no overlap
            "footer":       (0,  90, 100, 10),
        }
    ),
    "dashboard": TemplateLayout(
        name="dashboard",
        regions={
            "navbar":       (0,  0,  100, 9),    # Top navbar
            "sidebar":      (0,  9,  20,  91),   # Left sidebar
            "main":         (21, 9,  79,  45),   # Card grid — upper main area
            "content":      (21, 55, 79,  45),   # Table / secondary — lower main area
            "list_content": (21, 55, 79,  45),   # Alias
        }
    ),
    "list": TemplateLayout(
        name="list",
        regions={
            "navbar":       (0,  0,  100, 9),
            "filters":      (0,  9,  100, 11),   # Search bar
            "list_content": (0,  20, 100, 80),
            "content":      (0,  20, 100, 80),
            "main":         (0,  20, 100, 80),
        }
    ),
    "detail": TemplateLayout(
        name="detail",
        regions={
            "navbar":    (0,  0,  100, 9),
            "content":   (5,  11, 90,  73),      # Wide content area
            "actions":   (5,  86, 90,  10),
        }
    ),
    "form": TemplateLayout(
        name="form",
        regions={
            "navbar":       (0,  0,  100, 9),
            "form_content": (10, 11, 80,  70),
            "content":      (10, 11, 80,  70),
            "actions":      (10, 83, 80,  10),
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