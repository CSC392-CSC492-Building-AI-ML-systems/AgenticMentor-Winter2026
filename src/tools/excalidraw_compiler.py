
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
    SCREEN_PADDING = 150     # Space between screen frames (increased)
    GRID_SIZE = 20           # Snap-to-grid size
    
    # Enhanced color palette
    STROKE_COLOR = "#0f172a"        # Dark navy (sharper contrast)
    STROKE_LIGHT = "#cbd5e1"        # Light gray for subtle borders
    BACKGROUND_COLOR = "#f8fafc"    # Very light gray
    BACKGROUND_DARK = "#e2e8f0"     # Medium gray for contrast
    TEXT_COLOR = "#0f172a"          # Dark navy
    TEXT_MUTED = "#64748b"          # Muted gray for secondary text
    ACCENT_COLOR = "#2563eb"        # Vibrant blue
    ACCENT_HOVER = "#1e40af"        # Darker blue
    SUCCESS_COLOR = "#10b981"       # Green
    WARNING_COLOR = "#f59e0b"       # Orange
    
    # Typography
    FONT_HEADING = 1      # Excalidraw font family 1 (Hand-drawn)
    FONT_BODY = 1         # Same for consistency
    
    # Spacing & sizing
    PADDING_SM = 12
    PADDING_MD = 20
    PADDING_LG = 32
    BORDER_RADIUS = 8
    
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
        
        # 1. Screen frame (container rectangle) with drop shadow effect
        frame_id = self._generate_id()
        
        # Shadow (offset rectangle behind)
        elements.append({
            "id": self._generate_id(),
            "type": "rectangle",
            "x": x_offset + 4,
            "y": y_offset + 4,
            "width": self.SCREEN_WIDTH,
            "height": self.SCREEN_HEIGHT,
            "strokeColor": "transparent",
            "backgroundColor": "#00000020",
            "fillStyle": "solid",
            "strokeWidth": 0,
            "roughness": 0,
            "opacity": 40,
            "roundness": {"type": 3, "value": self.BORDER_RADIUS},
            "seed": self._generate_seed(),
            "version": 1,
            "versionNonce": self._generate_seed(),
            "isDeleted": False,
            "boundElements": [],
            "updated": self._timestamp(),
            "link": None,
            "locked": False,
        })
        
        # Main frame
        elements.append({
            "id": frame_id,
            "type": "rectangle",
            "x": x_offset,
            "y": y_offset,
            "width": self.SCREEN_WIDTH,
            "height": self.SCREEN_HEIGHT,
            "strokeColor": self.STROKE_LIGHT,
            "backgroundColor": "#ffffff",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "roughness": 0,
            "opacity": 100,
            "roundness": {"type": 3, "value": self.BORDER_RADIUS},
            "seed": self._generate_seed(),
            "version": 1,
            "versionNonce": self._generate_seed(),
            "isDeleted": False,
            "boundElements": [],
            "updated": self._timestamp(),
            "link": None,
            "locked": False,
        })
        
        # 2. Screen title with subtitle
        elements.append(self._create_text_element(
            x=x_offset + self.PADDING_MD,
            y=y_offset - 50,
            text=screen.screen_name,
            font_size=28,
            font_family=self.FONT_HEADING,
            text_color=self.STROKE_COLOR,
        ))
        
        # Subtitle (screen template type)
        elements.append(self._create_text_element(
            x=x_offset + self.PADDING_MD,
            y=y_offset - 20,
            text=f"Template: {screen.template}",
            font_size=14,
            font_family=self.FONT_BODY,
            text_color=self.TEXT_MUTED,
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
        """Render header component with gradient-like effect."""
        elements = []
        # Background with subtle gradient effect (darker top bar)
        elements.append(self._create_rectangle(
            x, y, w, 8, self.ACCENT_COLOR, stroke_width=0
        ))
        elements.append(self._create_rectangle(
            x, y + 8, w, h - 8, self.BACKGROUND_COLOR, stroke_width=0
        ))
        # Border
        elements.append(self._create_rectangle(
            x, y, w, h, "transparent", stroke_width=2, stroke_color=self.STROKE_LIGHT
        ))
        # Title text (centered)
        text_width = len(comp.label) * 20 * 0.6
        elements.append(self._create_text_element(
            x + (w - text_width) / 2, y + h/2 - 12, comp.label, 22, 
            font_family=self.FONT_HEADING, text_color=self.STROKE_COLOR
        ))
        return elements
    
    def render_navbar(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render modern navigation bar with logo area."""
        elements = []
        # Dark navbar background
        elements.append(self._create_rectangle(x, y, w, h, self.STROKE_COLOR, stroke_width=0))
        
        # Logo/brand area (left side)
        elements.append(self._create_text_element(
            x + self.PADDING_LG, y + h/2 - 12, comp.label, 20, 
            text_color="#ffffff", font_family=self.FONT_HEADING
        ))
        
        # Menu items (right side)
        menu_items = ["Home", "Dashboard", "Settings"]
        item_width = 100
        start_x = x + w - (len(menu_items) * item_width) - self.PADDING_LG
        for idx, item in enumerate(menu_items):
            item_x = start_x + idx * item_width
            elements.append(self._create_text_element(
                item_x, y + h/2 - 10, item, 16, text_color="#ffffff"
            ))
        
        return elements
    
    def render_sidebar(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render modern sidebar with icons and hover states."""
        elements = []
        # Sidebar background
        elements.append(self._create_rectangle(
            x, y, w, h, self.BACKGROUND_DARK, stroke_width=0
        ))
        # Right border
        elements.append(self._create_line(x + w, y, x + w, y + h))
        
        # Section title
        elements.append(self._create_text_element(
            x + self.PADDING_MD, y + self.PADDING_MD, "MENU", 12, 
            text_color=self.TEXT_MUTED
        ))
        
        # Render children as menu items with better spacing
        if comp.children:
            item_height = 48
            start_y = y + 60
            for idx, child in enumerate(comp.children):
                item_y = start_y + idx * item_height
                
                # Active state for first item
                if idx == 0:
                    elements.append(self._create_rectangle(
                        x + 8, item_y - 8, w - 16, 40, self.ACCENT_COLOR, stroke_width=0
                    ))
                    text_color = "#ffffff"
                else:
                    text_color = self.TEXT_COLOR
                
                # Icon placeholder (circle)
                elements.append(self._create_circle(
                    x + self.PADDING_MD, item_y + 4, 6, text_color
                ))
                
                # Menu item text
                elements.append(self._create_text_element(
                    x + self.PADDING_MD + 20, item_y, child, 16, text_color=text_color
                ))
        
        return elements
    
    def render_form(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render modern form with labels and styled inputs."""
        elements = []
        
        # Form container with subtle background
        elements.append(self._create_rectangle(
            x, y, w, h, self.BACKGROUND_COLOR, stroke_width=1, stroke_color=self.STROKE_LIGHT
        ))
        
        # Form title with underline
        elements.append(self._create_text_element(
            x + self.PADDING_LG, y + self.PADDING_LG, comp.label, 22, 
            font_family=self.FONT_HEADING, text_color=self.STROKE_COLOR
        ))
        elements.append(self._create_line(
            x + self.PADDING_LG, y + self.PADDING_LG + 30, 
            x + self.PADDING_LG + len(comp.label) * 13, y + self.PADDING_LG + 30
        ))
        
        # Render fields with better spacing
        if comp.children:
            field_height = 72
            start_y = y + 80
            max_fields = min(len(comp.children), int((h - 180) / field_height))
            
            for idx in range(max_fields):
                field_name = comp.children[idx]
                field_y = start_y + idx * field_height
                
                # Field label (bold)
                elements.append(self._create_text_element(
                    x + self.PADDING_LG, field_y, field_name, 14, 
                    text_color=self.STROKE_COLOR, font_family=self.FONT_HEADING
                ))
                
                # Input box with focus state styling
                input_bg = "#ffffff" if idx != 0 else "#eff6ff"
                input_stroke = self.STROKE_LIGHT if idx != 0 else self.ACCENT_COLOR
                elements.append(self._create_rectangle(
                    x + self.PADDING_LG, field_y + 24, w - 2 * self.PADDING_LG, 40,
                    input_bg, stroke_width=2, stroke_color=input_stroke
                ))
                
                # Placeholder text (if first field)
                if idx == 0:
                    elements.append(self._create_text_element(
                        x + self.PADDING_LG + 12, field_y + 36, 
                        f"Enter {field_name.lower()}...", 12, text_color=self.TEXT_MUTED
                    ))
        
        return elements
    
    def render_table(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render modern table with alternating row colors."""
        elements = []
        
        # Table container
        elements.append(self._create_rectangle(
            x, y, w, h, "#ffffff", stroke_width=1, stroke_color=self.STROKE_LIGHT
        ))
        
        # Header row with darker background
        header_height = 48
        elements.append(self._create_rectangle(
            x, y, w, header_height, self.BACKGROUND_DARK, stroke_width=0
        ))
        
        # Column headers with icons
        if comp.children:
            col_width = w / len(comp.children)
            for idx, col_name in enumerate(comp.children):
                col_x = x + idx * col_width + self.PADDING_MD
                # Header text
                elements.append(self._create_text_element(
                    col_x, y + 18, col_name, 14, 
                    text_color=self.STROKE_COLOR, font_family=self.FONT_HEADING
                ))
                # Sort indicator (small triangle for first column)
                if idx == 0:
                    elements.append(self._create_text_element(
                        col_x + len(col_name) * 8 + 4, y + 18, "▼", 10, 
                        text_color=self.TEXT_MUTED
                    ))
                
                # Column dividers
                if idx > 0:
                    col_line_x = x + idx * col_width
                    elements.append(self._create_line(
                        col_line_x, y, col_line_x, y + header_height
                    ))
        
        # Data rows with alternating colors
        row_height = 44
        num_rows = min(6, int((h - header_height) / row_height))
        for row_idx in range(num_rows):
            row_y = y + header_height + row_idx * row_height
            
            # Alternating row background
            if row_idx % 2 == 0:
                elements.append(self._create_rectangle(
                    x, row_y, w, row_height, self.BACKGROUND_COLOR, stroke_width=0
                ))
            
            # Row divider
            elements.append(self._create_line(
                x, row_y, x + w, row_y, stroke_color=self.STROKE_LIGHT
            ))
            
            # Sample data dots (to indicate content)
            if comp.children:
                for idx in range(len(comp.children)):
                    col_x = x + idx * col_width + self.PADDING_MD
                    elements.append(self._create_circle(
                        col_x, row_y + row_height/2 - 2, 3, self.TEXT_MUTED
                    ))
        
        return elements
    
    def render_card_grid(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render modern card grid with shadows and icons."""
        elements = []
        
        card_count = comp.metadata.get("card_count", 3) if comp.metadata else 3
        cards_per_row = 3
        card_margin = 24
        card_width = (w - (cards_per_row + 1) * card_margin) / cards_per_row
        card_height = 140
        
        for idx in range(card_count):
            row = idx // cards_per_row
            col = idx % cards_per_row
            card_x = x + card_margin + col * (card_width + card_margin)
            card_y = y + card_margin + row * (card_height + card_margin)
            
            # Card shadow
            elements.append(self._create_rectangle(
                card_x + 2, card_y + 2, card_width, card_height, 
                "#00000015", stroke_width=0
            ))
            
            # Card background
            elements.append(self._create_rectangle(
                card_x, card_y, card_width, card_height, "#ffffff", 
                stroke_width=1, stroke_color=self.STROKE_LIGHT
            ))
            
            # Colored accent bar on top
            accent_colors = [self.ACCENT_COLOR, self.SUCCESS_COLOR, self.WARNING_COLOR]
            elements.append(self._create_rectangle(
                card_x, card_y, card_width, 6, accent_colors[idx % 3], stroke_width=0
            ))
            
            # Icon circle
            icon_size = 40
            elements.append(self._create_circle(
                card_x + self.PADDING_MD + icon_size/2, 
                card_y + self.PADDING_LG + icon_size/2, 
                icon_size/2, accent_colors[idx % 3]
            ))
            
            # Card title
            elements.append(self._create_text_element(
                card_x + self.PADDING_MD, card_y + 70, 
                f"{comp.label} {idx + 1}", 16, 
                text_color=self.STROKE_COLOR, font_family=self.FONT_HEADING
            ))
            
            # Card value/metric (large number)
            elements.append(self._create_text_element(
                card_x + self.PADDING_MD, card_y + 95, 
                f"{(idx + 1) * 123}", 24, 
                text_color=accent_colors[idx % 3], font_family=self.FONT_HEADING
            ))
        
        return elements
    
    def render_button_group(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render modern button group with primary/secondary styles."""
        elements = []
        
        button_count = comp.metadata.get("button_count", 2) if comp.metadata else 2
        button_width = 140
        button_height = 44
        button_margin = 16
        
        # Center buttons
        total_width = button_count * button_width + (button_count - 1) * button_margin
        start_x = x + (w - total_width) / 2
        button_y = y + (h - button_height) / 2
        
        button_labels = ["Submit", "Cancel", "Reset", "Delete"]
        
        for idx in range(button_count):
            btn_x = start_x + idx * (button_width + button_margin)
            
            # Primary button (first one)
            if idx == 0:
                # Shadow
                elements.append(self._create_rectangle(
                    btn_x + 2, button_y + 2, button_width, button_height,
                    "#00000020", stroke_width=0
                ))
                # Button
                elements.append(self._create_rectangle(
                    btn_x, button_y, button_width, button_height,
                    self.ACCENT_COLOR, stroke_width=0
                ))
                text_color = "#ffffff"
            # Secondary button
            else:
                elements.append(self._create_rectangle(
                    btn_x, button_y, button_width, button_height,
                    "#ffffff", stroke_width=2, stroke_color=self.STROKE_LIGHT
                ))
                text_color = self.STROKE_COLOR
            
            # Button text (centered)
            btn_label = button_labels[idx] if idx < len(button_labels) else f"Action {idx + 1}"
            text_width = len(btn_label) * 14 * 0.6
            elements.append(self._create_text_element(
                btn_x + (button_width - text_width) / 2, 
                button_y + 16, 
                btn_label, 16,
                text_color=text_color, font_family=self.FONT_HEADING
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
        """Render modern search bar with icon."""
        elements = []
        
        # Search input with icon
        input_width = w * 0.75
        input_height = min(h, 48)
        
        # Input background
        elements.append(self._create_rectangle(
            x, y, input_width, input_height, "#ffffff", 
            stroke_width=2, stroke_color=self.STROKE_LIGHT
        ))
        
        # Search icon (circle with line)
        icon_x = x + 16
        icon_y = y + input_height/2
        elements.append(self._create_circle(icon_x, icon_y, 8, self.TEXT_MUTED))
        elements.append(self._create_line(
            icon_x + 6, icon_y + 6, icon_x + 10, icon_y + 10, stroke_color=self.TEXT_MUTED
        ))
        
        # Placeholder text
        elements.append(self._create_text_element(
            x + 40, y + input_height/2 - 10, comp.label, 14, text_color=self.TEXT_MUTED
        ))
        
        # Search button
        button_x = x + input_width + 12
        button_width = w - input_width - 12
        
        # Button shadow
        elements.append(self._create_rectangle(
            button_x + 2, y + 2, button_width, input_height,
            "#00000020", stroke_width=0
        ))
        
        # Button
        elements.append(self._create_rectangle(
            button_x, y, button_width, input_height, self.ACCENT_COLOR, stroke_width=0
        ))
        
        # Button text (centered)
        btn_text = "Search"
        text_width = len(btn_text) * 16 * 0.6
        elements.append(self._create_text_element(
            button_x + (button_width - text_width) / 2, 
            y + input_height/2 - 10, 
            btn_text, 16, 
            text_color="#ffffff", font_family=self.FONT_HEADING
        ))
        
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
        bg_color: str = "#ffffff", stroke_width: int = 2, stroke_color: str = None
    ) -> Dict[str, Any]:
        """Create Excalidraw rectangle element."""
        if stroke_color is None:
            stroke_color = self.STROKE_COLOR
        
        return {
            "id": self._generate_id(),
            "type": "rectangle",
            "x": round(x),
            "y": round(y),
            "width": round(w),
            "height": round(h),
            "angle": 0,
            "strokeColor": stroke_color,
            "backgroundColor": bg_color,
            "fillStyle": "solid",
            "strokeWidth": stroke_width,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "groupIds": [],
            "roundness": {"type": 3, "value": 4},
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
    
    def _create_line(self, x1: float, y1: float, x2: float, y2: float, stroke_color: str = None) -> Dict[str, Any]:
        """Create Excalidraw line element."""
        if stroke_color is None:
            stroke_color = self.STROKE_LIGHT
        
        return {
            "id": self._generate_id(),
            "type": "line",
            "x": round(x1),
            "y": round(y1),
            "width": round(x2 - x1),
            "height": 0,
            "angle": 0,
            "strokeColor": stroke_color,
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
    
    def _create_circle(self, x: float, y: float, radius: float, color: str) -> Dict[str, Any]:
        """Create Excalidraw circle (ellipse) element."""
        return {
            "id": self._generate_id(),
            "type": "ellipse",
            "x": round(x - radius),
            "y": round(y - radius),
            "width": round(radius * 2),
            "height": round(radius * 2),
            "angle": 0,
            "strokeColor": color,
            "backgroundColor": color,
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
        }
    
    def _create_arrow(self, x1: float, y1: float, x2: float, y2: float) -> Dict[str, Any]:
        """Create Excalidraw arrow element with modern styling."""
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
            "strokeWidth": 3,
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