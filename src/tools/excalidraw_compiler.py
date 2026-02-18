
from typing import List, Dict, Any
import uuid
from datetime import datetime

from src.models.wireframe_spec import WireframeSpec, ScreenSpec, ComponentSpec, NavigationLink
from src.tools.wireframe_template import TEMPLATES, COMPONENT_RENDERERS, TemplateLayout

class ExcalidrawCompiler:
    """Compiles WireframeSpec into Excalidraw JSON."""
    
    # Canvas constants
    SCREEN_WIDTH = 1200      # Fixed width per screen frame
    SCREEN_HEIGHT = 800      # Fixed height per screen frame
    SCREEN_PADDING = 100     # Space between screen frames
    GRID_SIZE = 20           # Snap-to-grid size
    
    # Component styling
    STROKE_COLOR = "#1e293b"     # Dark gray
    BACKGROUND_COLOR = "#f1f5f9"  # Light gray
    TEXT_COLOR = "#0f172a"
    ACCENT_COLOR = "#3b82f6"      # Blue
    
    def compile(self, spec: WireframeSpec) -> Dict[str, Any]:
        """Transform WireframeSpec into Excalidraw JSON."""
        elements = []
        
        # Position screens horizontally with padding
        for idx, screen_spec in enumerate(spec.screens):
            x_offset = idx * (self.SCREEN_WIDTH + self.SCREEN_PADDING)
            screen_elements = self._render_screen(screen_spec, x_offset, 0)
            elements.extend(screen_elements)
        
        # Add navigation arrows
        nav_elements = self._render_navigation(spec.screens, spec.navigation)
        elements.extend(nav_elements)
        
        return {
            "type": "excalidraw",
            "version": 2,
            "source": "https://excalidraw.com",
            "elements": elements,
            "appState": {
                "gridSize": self.GRID_SIZE,
                "viewBackgroundColor": "#ffffff",
                "currentItemStrokeColor": self.STROKE_COLOR,
                "currentItemBackgroundColor": self.BACKGROUND_COLOR,
            },
            "files": {},
        }
    
    def _render_screen(
        self, screen: ScreenSpec, x_offset: int, y_offset: int
    ) -> List[Dict[str, Any]]:
        """Render a single screen as Excalidraw elements."""
        elements = []
        
        # 1. Screen frame (container rectangle)
        frame_id = self._generate_id()
        elements.append({
            "id": frame_id,
            "type": "rectangle",
            "x": x_offset,
            "y": y_offset,
            "width": self.SCREEN_WIDTH,
            "height": self.SCREEN_HEIGHT,
            "strokeColor": self.STROKE_COLOR,
            "backgroundColor": "#ffffff",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "roughness": 0,
            "opacity": 100,
            "roundness": {"type": 2},
            "seed": self._generate_seed(),
            "version": 1,
            "versionNonce": self._generate_seed(),
            "isDeleted": False,
            "boundElements": [],
            "updated": self._timestamp(),
            "link": None,
            "locked": False,
        })
        
        # 2. Screen title
        elements.append(self._create_text_element(
            x=x_offset + 20,
            y=y_offset - 40,
            text=screen.screen_name,
            font_size=24,
            font_family=1,
        ))
        
        # 3. Get template layout
        template = TEMPLATES.get(screen.template, TEMPLATES["blank"])
        
        # 4. Render components using template regions
        for component_spec in screen.components:
            region_name = self._map_component_to_region(component_spec.type, template)
            if region_name not in template.regions:
                region_name = "content"  # fallback
            
            region_x_pct, region_y_pct, region_w_pct, region_h_pct = template.regions[region_name]
            
            # Convert percentages to absolute coordinates
            comp_x = x_offset + (region_x_pct / 100) * self.SCREEN_WIDTH
            comp_y = y_offset + (region_y_pct / 100) * self.SCREEN_HEIGHT
            comp_w = (region_w_pct / 100) * self.SCREEN_WIDTH
            comp_h = (region_h_pct / 100) * self.SCREEN_HEIGHT
            
            # Render component
            comp_elements = self._render_component(
                component_spec, comp_x, comp_y, comp_w, comp_h
            )
            elements.extend(comp_elements)
        
        return elements
    
    def _render_component(
        self, comp: ComponentSpec, x: float, y: float, w: float, h: float
    ) -> List[Dict[str, Any]]:
        """Render a component based on type."""
        renderer_name = COMPONENT_RENDERERS.get(comp.type, "render_generic")
        renderer = getattr(self, renderer_name, self.render_generic)
        return renderer(comp, x, y, w, h)
    
    # Component renderers
    
    def render_header(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render header component."""
        elements = []
        # Background rectangle
        elements.append(self._create_rectangle(x, y, w, h, self.BACKGROUND_COLOR))
        # Title text
        elements.append(self._create_text_element(x + 20, y + h/2 - 10, comp.label, 20))
        return elements
    
    def render_navbar(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render navigation bar."""
        elements = []
        elements.append(self._create_rectangle(x, y, w, h, self.STROKE_COLOR))
        elements.append(self._create_text_element(
            x + 20, y + h/2 - 10, comp.label, 18, text_color="#ffffff"
        ))
        return elements
    
    def render_sidebar(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render sidebar with menu items."""
        elements = []
        elements.append(self._create_rectangle(x, y, w, h, self.BACKGROUND_COLOR))
        
        # Render children as menu items
        if comp.children:
            item_height = min(50, h / len(comp.children))
            for idx, child in enumerate(comp.children):
                item_y = y + idx * item_height + 10
                elements.append(self._create_text_element(x + 20, item_y, child, 16))
        
        return elements
    
    def render_form(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render form with fields."""
        elements = []
        
        # Form container
        elements.append(self._create_rectangle(x, y, w, h, "#ffffff", stroke_width=1))
        
        # Form title
        elements.append(self._create_text_element(x + 20, y + 20, comp.label, 18))
        
        # Render fields
        if comp.children:
            field_height = 60
            start_y = y + 60
            for idx, field_name in enumerate(comp.children):
                field_y = start_y + idx * field_height
                # Field label
                elements.append(self._create_text_element(x + 20, field_y, field_name, 14))
                # Input box
                elements.append(self._create_rectangle(
                    x + 20, field_y + 20, w - 40, 35, "#ffffff", stroke_width=1
                ))
        
        return elements
    
    def render_table(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render table with columns."""
        elements = []
        
        # Table container
        elements.append(self._create_rectangle(x, y, w, h, "#ffffff", stroke_width=1))
        
        # Header row
        header_height = 40
        elements.append(self._create_rectangle(x, y, w, header_height, self.BACKGROUND_COLOR))
        
        # Column headers
        if comp.children:
            col_width = w / len(comp.children)
            for idx, col_name in enumerate(comp.children):
                col_x = x + idx * col_width + 10
                elements.append(self._create_text_element(col_x, y + 15, col_name, 14))
        
        # Data rows (placeholder)
        row_height = 40
        num_rows = min(5, int((h - header_height) / row_height))
        for row_idx in range(num_rows):
            row_y = y + header_height + row_idx * row_height
            elements.append(self._create_line(x, row_y, x + w, row_y))
        
        return elements
    
    def render_card_grid(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render grid of cards."""
        elements = []
        
        card_count = comp.metadata.get("card_count", 3) if comp.metadata else 3
        cards_per_row = 3
        card_margin = 20
        card_width = (w - (cards_per_row + 1) * card_margin) / cards_per_row
        card_height = 120
        
        for idx in range(card_count):
            row = idx // cards_per_row
            col = idx % cards_per_row
            card_x = x + card_margin + col * (card_width + card_margin)
            card_y = y + card_margin + row * (card_height + card_margin)
            
            # Card rectangle
            elements.append(self._create_rectangle(
                card_x, card_y, card_width, card_height, "#ffffff", stroke_width=1
            ))
            # Card label
            elements.append(self._create_text_element(
                card_x + 20, card_y + 20, f"{comp.label} {idx + 1}", 16
            ))
        
        return elements
    
    def render_button_group(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render group of buttons."""
        elements = []
        
        button_count = comp.metadata.get("button_count", 2) if comp.metadata else 2
        button_width = 120
        button_height = 40
        button_margin = 20
        
        # Center buttons
        total_width = button_count * button_width + (button_count - 1) * button_margin
        start_x = x + (w - total_width) / 2
        button_y = y + (h - button_height) / 2
        
        for idx in range(button_count):
            btn_x = start_x + idx * (button_width + button_margin)
            elements.append(self._create_rectangle(
                btn_x, button_y, button_width, button_height,
                self.ACCENT_COLOR if idx == 0 else "#ffffff",
                stroke_width=2
            ))
            btn_label = "Submit" if idx == 0 else "Cancel"
            elements.append(self._create_text_element(
                btn_x + button_width/2 - 30, button_y + 15, btn_label, 14,
                text_color="#ffffff" if idx == 0 else self.TEXT_COLOR
            ))
        
        return elements
    
    def render_hero(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render hero section."""
        elements = []
        elements.append(self._create_rectangle(x, y, w, h, self.BACKGROUND_COLOR, stroke_width=1))
        elements.append(self._create_text_element(x + w/2 - 50, y + h/2 - 20, comp.label, 24))
        return elements
    
    def render_detail_view(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render detail view."""
        elements = []
        elements.append(self._create_rectangle(x, y, w, h, "#ffffff", stroke_width=1))
        elements.append(self._create_text_element(x + 20, y + 20, comp.label, 18))
        
        # Add some detail fields
        if comp.children:
            field_y = y + 60
            for child in comp.children:
                elements.append(self._create_text_element(x + 20, field_y, f"{child}:", 14))
                field_y += 30
        
        return elements
    
    def render_footer(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render footer."""
        elements = []
        elements.append(self._create_rectangle(x, y, w, h, self.STROKE_COLOR))
        elements.append(self._create_text_element(x + w/2 - 30, y + h/2 - 10, comp.label, 14, text_color="#ffffff"))
        return elements
    
    def render_tabs(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render tabs."""
        elements = []
        
        if comp.children:
            tab_width = w / len(comp.children)
            for idx, tab_name in enumerate(comp.children):
                tab_x = x + idx * tab_width
                # Tab background
                bg_color = self.ACCENT_COLOR if idx == 0 else self.BACKGROUND_COLOR
                elements.append(self._create_rectangle(tab_x, y, tab_width, 40, bg_color, stroke_width=1))
                # Tab label
                text_color = "#ffffff" if idx == 0 else self.TEXT_COLOR
                elements.append(self._create_text_element(tab_x + 20, y + 15, tab_name, 14, text_color=text_color))
        
        # Content area
        elements.append(self._create_rectangle(x, y + 40, w, h - 40, "#ffffff", stroke_width=1))
        
        return elements
    
    def render_search_bar(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render search bar."""
        elements = []
        
        # Search input
        input_width = w * 0.7
        elements.append(self._create_rectangle(x, y, input_width, h, "#ffffff", stroke_width=1))
        elements.append(self._create_text_element(x + 10, y + h/2 - 10, comp.label, 14))
        
        # Search button
        button_x = x + input_width + 10
        button_width = w - input_width - 10
        elements.append(self._create_rectangle(button_x, y, button_width, h, self.ACCENT_COLOR, stroke_width=2))
        elements.append(self._create_text_element(button_x + 20, y + h/2 - 10, "Search", 14, text_color="#ffffff"))
        
        return elements
    
    def render_generic(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Fallback renderer."""
        elements = []
        elements.append(self._create_rectangle(x, y, w, h, self.BACKGROUND_COLOR, stroke_width=1))
        elements.append(self._create_text_element(x + 20, y + 20, comp.label, 14))
        return elements
    
    def _render_navigation(
        self, screens: List[ScreenSpec], navigation: List[NavigationLink]
    ) -> List[Dict[str, Any]]:
        """Render navigation arrows between screens."""
        elements = []
        
        # Build screen position map
        screen_positions = {}
        for idx, screen in enumerate(screens):
            x = idx * (self.SCREEN_WIDTH + self.SCREEN_PADDING)
            screen_positions[screen.screen_id] = (
                x + self.SCREEN_WIDTH / 2,  # center x
                self.SCREEN_HEIGHT + 50      # below screen
            )
        
        # Draw arrows
        for nav in navigation:
            if nav.from_screen in screen_positions and nav.to_screen in screen_positions:
                from_x, from_y = screen_positions[nav.from_screen]
                to_x, to_y = screen_positions[nav.to_screen]
                
                elements.append(self._create_arrow(from_x, from_y, to_x, to_y))
                # Arrow label
                mid_x = (from_x + to_x) / 2
                mid_y = (from_y + to_y) / 2 - 20
                elements.append(self._create_text_element(mid_x, mid_y, nav.trigger, 12))
        
        return elements
    
    # Helper methods for creating Excalidraw elements
    
    def _create_rectangle(
        self, x: float, y: float, w: float, h: float,
        bg_color: str = "#ffffff", stroke_width: int = 2
    ) -> Dict[str, Any]:
        """Create Excalidraw rectangle element."""
        return {
            "id": self._generate_id(),
            "type": "rectangle",
            "x": round(x),
            "y": round(y),
            "width": round(w),
            "height": round(h),
            "angle": 0,
            "strokeColor": self.STROKE_COLOR,
            "backgroundColor": bg_color,
            "fillStyle": "solid",
            "strokeWidth": stroke_width,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "groupIds": [],
            "roundness": {"type": 2},
            "seed": self._generate_seed(),
            "version": 1,
            "versionNonce": self._generate_seed(),
            "isDeleted": False,
            "boundElements": None,
            "updated": self._timestamp(),
            "link": None,
            "locked": False,
        }
    
    def _create_text_element(
        self, x: float, y: float, text: str, font_size: int = 16,
        text_color: str = None, font_family: int = 1
    ) -> Dict[str, Any]:
        """Create Excalidraw text element."""
        return {
            "id": self._generate_id(),
            "type": "text",
            "x": round(x),
            "y": round(y),
            "width": len(text) * font_size * 0.6,  # Approximate width
            "height": font_size * 1.2,
            "angle": 0,
            "strokeColor": text_color or self.TEXT_COLOR,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "groupIds": [],
            "roundness": None,
            "seed": self._generate_seed(),
            "version": 1,
            "versionNonce": self._generate_seed(),
            "isDeleted": False,
            "boundElements": None,
            "updated": self._timestamp(),
            "link": None,
            "locked": False,
            "text": text,
            "fontSize": font_size,
            "fontFamily": font_family,
            "textAlign": "left",
            "verticalAlign": "top",
            "baseline": font_size,
            "containerId": None,
            "originalText": text,
            "lineHeight": 1.25,
        }
    
    def _create_line(self, x1: float, y1: float, x2: float, y2: float) -> Dict[str, Any]:
        """Create Excalidraw line element."""
        return {
            "id": self._generate_id(),
            "type": "line",
            "x": round(x1),
            "y": round(y1),
            "width": round(x2 - x1),
            "height": 0,
            "angle": 0,
            "strokeColor": self.STROKE_COLOR,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "groupIds": [],
            "roundness": {"type": 2},
            "seed": self._generate_seed(),
            "version": 1,
            "versionNonce": self._generate_seed(),
            "isDeleted": False,
            "boundElements": None,
            "updated": self._timestamp(),
            "link": None,
            "locked": False,
            "points": [[0, 0], [round(x2 - x1), 0]],
            "lastCommittedPoint": None,
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": None,
            "endArrowhead": None,
        }
    
    def _create_arrow(self, x1: float, y1: float, x2: float, y2: float) -> Dict[str, Any]:
        """Create Excalidraw arrow element."""
        return {
            "id": self._generate_id(),
            "type": "arrow",
            "x": round(x1),
            "y": round(y1),
            "width": round(x2 - x1),
            "height": round(y2 - y1),
            "angle": 0,
            "strokeColor": self.ACCENT_COLOR,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "groupIds": [],
            "roundness": {"type": 2},
            "seed": self._generate_seed(),
            "version": 1,
            "versionNonce": self._generate_seed(),
            "isDeleted": False,
            "boundElements": None,
            "updated": self._timestamp(),
            "link": None,
            "locked": False,
            "points": [[0, 0], [round(x2 - x1), round(y2 - y1)]],
            "lastCommittedPoint": None,
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": None,
            "endArrowhead": "arrow",
        }
    
    def _map_component_to_region(self, comp_type: str, template: TemplateLayout) -> str:
        """Map component type to template region."""
        mapping = {
            "header": "header",
            "navbar": "navbar",
            "sidebar": "sidebar",
            "hero": "content",
            "form": "form_content" if "form_content" in template.regions else "content",
            "table": "list_content" if "list_content" in template.regions else "main",
            "card_grid": "main" if "main" in template.regions else "content",
            "detail_view": "content",
            "footer": "footer",
            "tabs": "content",
            "button_group": "actions" if "actions" in template.regions else "content",
            "search_bar": "filters" if "filters" in template.regions else "content",
        }
        return mapping.get(comp_type, "content")
    
    def _generate_id(self) -> str:
        """Generate Excalidraw element ID."""
        return str(uuid.uuid4()).replace("-", "")[:20]
    
    def _generate_seed(self) -> int:
        """Generate random seed for Excalidraw."""
        import random
        return random.randint(1000000000, 9999999999)
    
    def _timestamp(self) -> int:
        """Current timestamp in milliseconds."""
        return int(datetime.utcnow().timestamp() * 1000)