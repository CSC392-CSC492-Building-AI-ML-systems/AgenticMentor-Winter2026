
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
    SCREEN_PADDING = 200     # More space between screens
    GRID_SIZE = 20           # Snap-to-grid size
    
    # Wireframe/Paper sketch color palette (black & gray only)
    STROKE_COLOR = "#1a1a1a"        # Dark charcoal (pencil)
    STROKE_MEDIUM = "#4a4a4a"       # Medium gray
    STROKE_LIGHT = "#9ca3af"        # Light gray (faint lines)
    BACKGROUND_COLOR = "#fafafa"    # Almost white (paper)
    BACKGROUND_GRAY = "#f5f5f5"     # Light gray fill
    TEXT_COLOR = "#1a1a1a"          # Dark charcoal
    TEXT_LIGHT = "#6b7280"          # Light gray text
    ACCENT_COLOR = "#1a1a1a"        # Same as stroke (no blue!)
    HIGHLIGHT_COLOR = "#4a4a4a"     # Medium gray for emphasis
    
    # Typography (larger sizes)
    FONT_HEADING = 1      # Excalidraw font family 1 (Hand-drawn)
    FONT_BODY = 1         # Same for consistency
    
    # Base font sizes (increased)
    FONT_XL = 32          # Extra large (screen titles)
    FONT_LG = 24          # Large (section headers)
    FONT_MD = 18          # Medium (body text)
    FONT_SM = 14          # Small (labels)
    FONT_XS = 12          # Extra small (hints)
    
    # Spacing & sizing (more generous)
    PADDING_SM = 16
    PADDING_MD = 28
    PADDING_LG = 44
    BORDER_RADIUS = 4     # Subtle rounded corners
    
    # Sketch style
    ROUGHNESS = 1         # Hand-drawn feel (0-2, higher = sketchier)
    
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
        
        # 1. Screen frame (simple sketch style - no shadow)
        frame_id = self._generate_id()
        
        # Main frame — solid white so components sit on clean paper
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
            "roughness": self.ROUGHNESS,
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
        
        # 2. Screen title (larger, hand-written style)
        elements.append(self._create_text_element(
            x=x_offset + self.PADDING_LG,
            y=y_offset - 60,
            text=screen.screen_name,
            font_size=self.FONT_XL,
            font_family=self.FONT_HEADING,
            text_color=self.STROKE_COLOR,
        ))
        
        # Underline (hand-drawn)
        title_width = len(screen.screen_name) * self.FONT_XL * 0.5
        elements.append(self._create_line(
            x_offset + self.PADDING_LG, 
            y_offset - 20,
            x_offset + self.PADDING_LG + title_width,
            y_offset - 20,
            stroke_color=self.STROKE_LIGHT
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
        """Render header component (sketch style)."""
        elements = []
        # Solid fill — hachure on gray looks noisy
        elements.append(self._create_rectangle(
            x, y, w, h, self.BACKGROUND_GRAY, stroke_width=2, fill_style="solid"
        ))
        # Title text (centered, larger)
        text_width = len(comp.label) * self.FONT_LG * 0.55
        elements.append(self._create_text_element(
            x + (w - text_width) / 2, y + h/2 - 14, comp.label, self.FONT_LG, 
            font_family=self.FONT_HEADING, text_color=self.STROKE_COLOR
        ))
        return elements
    
    def render_navbar(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render navigation bar (sketch style)."""
        elements = []
        # Solid fill — hachure on dark backgrounds makes text unreadable
        elements.append(self._create_rectangle(
            x, y, w, h, self.STROKE_COLOR, stroke_width=2, fill_style="solid"
        ))
        
        # Logo/brand text (left)
        elements.append(self._create_text_element(
            x + self.PADDING_LG, y + h/2 - 12, comp.label, self.FONT_LG, 
            text_color="#ffffff", font_family=self.FONT_HEADING
        ))
        
        # Menu items (right)
        menu_items = ["Home", "About", "Contact"]
        item_width = 120
        start_x = x + w - (len(menu_items) * item_width) - self.PADDING_LG
        for idx, item in enumerate(menu_items):
            item_x = start_x + idx * item_width
            elements.append(self._create_text_element(
                item_x, y + h/2 - 10, item, self.FONT_MD, text_color="#ffffff"
            ))
        
        return elements
    
    def render_sidebar(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render sidebar (sketch style)."""
        elements = []
        # Sidebar background — solid fill keeps it clean
        elements.append(self._create_rectangle(
            x, y, w, h, self.BACKGROUND_GRAY, stroke_width=2, fill_style="solid"
        ))
        
        # Section title (larger)
        elements.append(self._create_text_element(
            x + self.PADDING_MD, y + self.PADDING_MD, "MENU", self.FONT_SM, 
            text_color=self.TEXT_LIGHT
        ))
        
        # Render children as menu items (larger spacing and text)
        if comp.children:
            item_height = 56
            start_y = y + 70
            for idx, child in enumerate(comp.children):
                item_y = start_y + idx * item_height
                
                # Active state for first item — solid fill so text is visible
                if idx == 0:
                    elements.append(self._create_rectangle(
                        x + 8, item_y - 10, w - 16, 44, self.STROKE_COLOR,
                        stroke_width=2, fill_style="solid"
                    ))
                    text_color = "#ffffff"
                else:
                    text_color = self.TEXT_COLOR
                
                # Bullet point (simple dash)
                elements.append(self._create_text_element(
                    x + self.PADDING_MD, item_y, "—", self.FONT_MD, text_color=text_color
                ))
                
                # Menu item text (larger)
                elements.append(self._create_text_element(
                    x + self.PADDING_MD + 24, item_y, child, self.FONT_MD, text_color=text_color
                ))
        
        return elements
    
    def render_form(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render form (clean sketch style). Buttons live in the 'actions' region, not here."""
        elements = []
        
        # Form container — solid white so it reads cleanly
        elements.append(self._create_rectangle(
            x, y, w, h, "#ffffff", stroke_width=2, fill_style="solid"
        ))
        
        # Form title with hand-drawn underline
        elements.append(self._create_text_element(
            x + self.PADDING_LG, y + self.PADDING_MD, comp.label, self.FONT_LG, 
            font_family=self.FONT_HEADING, text_color=self.STROKE_COLOR
        ))
        title_width = len(comp.label) * self.FONT_LG * 0.5
        elements.append(self._create_line(
            x + self.PADDING_LG, y + self.PADDING_MD + 32, 
            x + self.PADDING_LG + title_width, y + self.PADDING_MD + 32,
            stroke_color=self.STROKE_LIGHT
        ))
        
        if comp.children:
            field_height = 76   # label (22) + input (44) + gap (10)
            start_y = y + self.PADDING_MD + 50
            # Use available height; leave 20px bottom margin
            available_h = h - (start_y - y) - 20
            max_fields = min(len(comp.children), max(1, int(available_h / field_height)))
            
            for idx in range(max_fields):
                field_name = comp.children[idx]
                field_y = start_y + idx * field_height
                
                # Field label
                elements.append(self._create_text_element(
                    x + self.PADDING_LG, field_y, field_name, self.FONT_MD, 
                    text_color=self.STROKE_COLOR, font_family=self.FONT_HEADING
                ))
                
                # Input box
                elements.append(self._create_rectangle(
                    x + self.PADDING_LG, field_y + 24, w - 2 * self.PADDING_LG, 42,
                    "#ffffff", stroke_width=2, stroke_color=self.STROKE_MEDIUM, fill_style="solid"
                ))
                
                # Placeholder text in first field only
                if idx == 0:
                    elements.append(self._create_text_element(
                        x + self.PADDING_LG + 12, field_y + 38, 
                        f"Enter {field_name.lower()}...", self.FONT_SM, 
                        text_color=self.TEXT_LIGHT
                    ))
        
        return elements
    
    def render_table(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render table (clean wireframe style)."""
        elements = []
        
        # Table container
        elements.append(self._create_rectangle(
            x, y, w, h, "#ffffff", stroke_width=2, fill_style="solid"
        ))
        
        # Header row
        header_height = 52
        elements.append(self._create_rectangle(
            x, y, w, header_height, self.BACKGROUND_GRAY, stroke_width=0, fill_style="solid"
        ))
        
        # Column headers (larger text)
        if comp.children:
            col_width = w / len(comp.children)
            for idx, col_name in enumerate(comp.children):
                col_x = x + idx * col_width + self.PADDING_MD
                # Header text (larger)
                elements.append(self._create_text_element(
                    col_x, y + 20, col_name, self.FONT_MD, 
                    text_color=self.STROKE_COLOR, font_family=self.FONT_HEADING
                ))
                
                # Column dividers (simple lines)
                if idx > 0:
                    col_line_x = x + idx * col_width
                    elements.append(self._create_line(
                        col_line_x, y, col_line_x, y + header_height,
                        stroke_color=self.STROKE_LIGHT
                    ))
        
        # Data rows (simple lines, more spacing)
        row_height = 48
        num_rows = min(6, int((h - header_height) / row_height))
        for row_idx in range(num_rows):
            row_y = y + header_height + row_idx * row_height
            
            # Row divider
            elements.append(self._create_line(
                x, row_y, x + w, row_y, stroke_color=self.STROKE_LIGHT
            ))
            
            # Sample data (simple dashes instead of dots)
            if comp.children:
                for idx in range(len(comp.children)):
                    col_x = x + idx * col_width + self.PADDING_MD
                    elements.append(self._create_text_element(
                        col_x, row_y + 18, "—", self.FONT_MD, 
                        text_color=self.TEXT_LIGHT
                    ))
        
        return elements
    
    def render_card_grid(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render card grid (sketch wireframe style)."""
        elements = []
        
        card_count = comp.metadata.get("card_count", 3) if comp.metadata else 3
        cards_per_row = 3
        card_margin = 32
        card_width = (w - (cards_per_row + 1) * card_margin) / cards_per_row
        card_height = 150
        
        for idx in range(card_count):
            row = idx // cards_per_row
            col = idx % cards_per_row
            card_x = x + card_margin + col * (card_width + card_margin)
            card_y = y + card_margin + row * (card_height + card_margin)
            
            # Card — solid fill so numbers are legible
            elements.append(self._create_rectangle(
                card_x, card_y, card_width, card_height, self.BACKGROUND_GRAY, 
                stroke_width=2, fill_style="solid"
            ))
            
            # Card title (larger text)
            elements.append(self._create_text_element(
                card_x + self.PADDING_MD, card_y + self.PADDING_MD, 
                f"{comp.label} {idx + 1}", self.FONT_MD, 
                text_color=self.STROKE_COLOR, font_family=self.FONT_HEADING
            ))
            
            # Separator line
            elements.append(self._create_line(
                card_x + self.PADDING_MD, card_y + self.PADDING_MD + 30,
                card_x + card_width - self.PADDING_MD, card_y + self.PADDING_MD + 30,
                stroke_color=self.STROKE_LIGHT
            ))
            
            # Large metric number (hand-drawn style)
            elements.append(self._create_text_element(
                card_x + self.PADDING_MD, card_y + 70, 
                f"{(idx + 1) * 123}", self.FONT_XL, 
                text_color=self.STROKE_COLOR, font_family=self.FONT_HEADING
            ))
            
            # Small label below
            elements.append(self._create_text_element(
                card_x + self.PADDING_MD, card_y + 110, 
                "Units", self.FONT_SM, text_color=self.TEXT_LIGHT
            ))
        
        return elements
    
    def render_button_group(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render button group (simple sketch style)."""
        elements = []
        
        button_count = comp.metadata.get("button_count", 2) if comp.metadata else 2
        button_width = 160
        button_height = 48
        button_margin = 20
        
        # Center buttons
        total_width = button_count * button_width + (button_count - 1) * button_margin
        start_x = x + (w - total_width) / 2
        button_y = y + (h - button_height) / 2
        
        button_labels = ["Submit", "Cancel", "Reset", "Delete"]
        
        for idx in range(button_count):
            btn_x = start_x + idx * (button_width + button_margin)
            
            if idx == 0:
                # Primary button — solid fill so white text is readable
                elements.append(self._create_rectangle(
                    btn_x, button_y, button_width, button_height,
                    self.STROKE_COLOR, stroke_width=2, fill_style="solid"
                ))
                text_color = "#ffffff"
            else:
                # Secondary button — outline only
                elements.append(self._create_rectangle(
                    btn_x, button_y, button_width, button_height,
                    "#ffffff", stroke_width=2, fill_style="solid"
                ))
                text_color = self.STROKE_COLOR
            
            # Button text (centered, larger)
            btn_label = button_labels[idx] if idx < len(button_labels) else f"Action {idx + 1}"
            text_width = len(btn_label) * self.FONT_MD * 0.55
            elements.append(self._create_text_element(
                btn_x + (button_width - text_width) / 2, 
                button_y + 18, 
                btn_label, self.FONT_MD,
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
        """Render detail view — structured card with header, field rows, and status."""
        elements = []
        
        # Card background
        elements.append(self._create_rectangle(
            x, y, w, h, "#ffffff", stroke_width=2, fill_style="solid"
        ))
        
        # Header band with title
        header_h = 56
        elements.append(self._create_rectangle(
            x, y, w, header_h, self.BACKGROUND_GRAY, stroke_width=0, fill_style="solid"
        ))
        elements.append(self._create_text_element(
            x + self.PADDING_LG, y + 18, comp.label, self.FONT_LG,
            font_family=self.FONT_HEADING, text_color=self.STROKE_COLOR
        ))
        
        # Build field rows — label column + value placeholder column
        field_labels = comp.children if comp.children else ["Title", "Description", "Status", "Created", "Updated"]
        row_h = 52
        start_y = y + header_h + 12
        label_col_w = w * 0.28
        
        for idx, label in enumerate(field_labels[:8]):  # cap at 8 rows
            row_y = start_y + idx * row_h
            if row_y + row_h > y + h - self.PADDING_SM:
                break
            
            # Subtle alternate background
            if idx % 2 == 0:
                elements.append(self._create_rectangle(
                    x, row_y, w, row_h, self.BACKGROUND_GRAY, stroke_width=0, fill_style="solid"
                ))
            
            # Label (left column)
            elements.append(self._create_text_element(
                x + self.PADDING_LG, row_y + 18,
                f"{label}", self.FONT_MD,
                text_color=self.TEXT_LIGHT, font_family=self.FONT_HEADING
            ))
            
            # Vertical divider between label and value
            elements.append(self._create_line(
                x + label_col_w, row_y, x + label_col_w, row_y + row_h,
                stroke_color=self.STROKE_LIGHT
            ))
            
            # Value placeholder box (right column)
            val_x = x + label_col_w + self.PADDING_MD
            val_w = w - label_col_w - self.PADDING_MD - self.PADDING_LG
            elements.append(self._create_rectangle(
                val_x, row_y + 12, val_w, 28,
                self.BACKGROUND_COLOR, stroke_width=1, stroke_color=self.STROKE_LIGHT, fill_style="solid"
            ))
            
            # Row divider
            elements.append(self._create_line(
                x, row_y + row_h, x + w, row_y + row_h, stroke_color=self.STROKE_LIGHT
            ))
        
        return elements
    
    def render_footer(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render footer."""
        elements = []
        elements.append(self._create_rectangle(
            x, y, w, h, self.STROKE_COLOR, stroke_width=2, fill_style="solid"
        ))
        text_width = len(comp.label) * self.FONT_SM * 0.55
        elements.append(self._create_text_element(
            x + (w - text_width) / 2, y + h/2 - 8, comp.label, self.FONT_SM, text_color="#ffffff"
        ))
        return elements
    
    def render_tabs(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render tabs."""
        elements = []
        tab_height = 44
        
        if comp.children:
            tab_width = w / len(comp.children)
            for idx, tab_name in enumerate(comp.children):
                tab_x = x + idx * tab_width
                if idx == 0:
                    # Active tab — solid fill
                    elements.append(self._create_rectangle(
                        tab_x, y, tab_width, tab_height,
                        self.STROKE_COLOR, stroke_width=2, fill_style="solid"
                    ))
                    text_color = "#ffffff"
                else:
                    elements.append(self._create_rectangle(
                        tab_x, y, tab_width, tab_height,
                        self.BACKGROUND_GRAY, stroke_width=2, fill_style="solid"
                    ))
                    text_color = self.TEXT_COLOR
                elements.append(self._create_text_element(
                    tab_x + self.PADDING_MD, y + 16, tab_name, self.FONT_MD, text_color=text_color
                ))
        
        # Content area
        elements.append(self._create_rectangle(
            x, y + tab_height, w, h - tab_height, "#ffffff", stroke_width=2, fill_style="solid"
        ))
        
        return elements
    
    def render_search_bar(self, comp: ComponentSpec, x: float, y: float, w: float, h: float):
        """Render search bar (simple wireframe)."""
        elements = []
        
        # Search input
        input_width = w * 0.75
        input_height = min(h, 52)
        
        # Input box (simple)
        elements.append(self._create_rectangle(
            x, y, input_width, input_height, self.BACKGROUND_COLOR, 
            stroke_width=2
        ))
        
        # Placeholder text (larger)
        elements.append(self._create_text_element(
            x + self.PADDING_MD, y + input_height/2 - 10, 
            comp.label, self.FONT_MD, text_color=self.TEXT_LIGHT
        ))
        
        # Search button (simple filled box)
        button_x = x + input_width + 16
        button_width = w - input_width - 16
        
        elements.append(self._create_rectangle(
            button_x, y, button_width, input_height, 
            self.STROKE_COLOR, stroke_width=2, fill_style="solid"
        ))
        
        # Button text (centered, larger)
        btn_text = "Search"
        text_width = len(btn_text) * self.FONT_MD * 0.55
        elements.append(self._create_text_element(
            button_x + (button_width - text_width) / 2, 
            y + input_height/2 - 10, 
            btn_text, self.FONT_MD, 
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
        """Render navigation arrows between screens (larger, sketch style)."""
        elements = []
        
        # Build screen position map
        screen_positions = {}
        for idx, screen in enumerate(screens):
            x = idx * (self.SCREEN_WIDTH + self.SCREEN_PADDING)
            screen_positions[screen.screen_id] = (
                x + self.SCREEN_WIDTH / 2,  # center x
                self.SCREEN_HEIGHT + 70      # below screen (more space)
            )
        
        # Draw arrows
        for nav in navigation:
            if nav.from_screen in screen_positions and nav.to_screen in screen_positions:
                from_x, from_y = screen_positions[nav.from_screen]
                to_x, to_y = screen_positions[nav.to_screen]
                
                elements.append(self._create_arrow(from_x, from_y, to_x, to_y))
                # Arrow label (larger text, more space above arrow)
                mid_x = (from_x + to_x) / 2
                mid_y = (from_y + to_y) / 2 - 30
                elements.append(self._create_text_element(
                    mid_x - len(nav.trigger) * self.FONT_MD * 0.3, 
                    mid_y, 
                    nav.trigger, 
                    self.FONT_MD,
                    text_color=self.STROKE_COLOR
                ))
        
        return elements
    
    # Helper methods for creating Excalidraw elements
    
    def _create_rectangle(
        self, x: float, y: float, w: float, h: float,
        bg_color: str = "#ffffff", stroke_width: int = 2,
        stroke_color: str = None, fill_style: str = None
    ) -> Dict[str, Any]:
        """Create Excalidraw rectangle element.
        
        fill_style: "hachure" for sketch/paper regions, "solid" for dark filled elements
                    (dark backgrounds with hachure = unreadable text)
        """
        if stroke_color is None:
            stroke_color = self.STROKE_COLOR
        if fill_style is None:
            fill_style = "hachure"
        
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
            "fillStyle": fill_style,
            "strokeWidth": stroke_width,
            "strokeStyle": "solid",
            "roughness": self.ROUGHNESS,
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
        """Create Excalidraw text element (sketch style)."""
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
            "roughness": self.ROUGHNESS,  # Hand-drawn feel
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
        """Create Excalidraw line element (sketch style)."""
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
            "roughness": self.ROUGHNESS,  # Hand-drawn feel
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
        """Create Excalidraw circle/ellipse element (sketch style)."""
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
            "roughness": self.ROUGHNESS,  # Hand-drawn feel
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
        """Create Excalidraw arrow element (larger, sketch style)."""
        return {
            "id": self._generate_id(),
            "type": "arrow",
            "x": round(x1),
            "y": round(y1),
            "width": round(x2 - x1),
            "height": round(y2 - y1),
            "angle": 0,
            "strokeColor": self.STROKE_COLOR,  # Black instead of blue
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 4,  # Thicker arrow
            "strokeStyle": "solid",
            "roughness": self.ROUGHNESS,  # Hand-drawn feel
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