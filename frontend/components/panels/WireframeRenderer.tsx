"use client";

interface Component {
  type: string;
  label?: string;
  children?: string[];
  metadata?: Record<string, any>;
}

interface WireframeRendererProps {
  screen: {
    screen_name?: string;
    template?: string;
    components?: Component[];
    notes?: string;
  };
}

function WireframeComponent({ comp }: { comp: Component }) {
  switch (comp.type) {
    case "header":
      return (
        <div style={{ background: "#3a3a3a", color: "#fff", padding: "12px 16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontWeight: 700, fontSize: 13, letterSpacing: 1 }}>{comp.label}</span>
          <div style={{ display: "flex", gap: 12 }}>
            <div style={{ width: 24, height: 24, background: "#666", borderRadius: "50%" }} />
            <div style={{ width: 60, height: 24, background: "#555", borderRadius: 4 }} />
          </div>
        </div>
      );

    case "navbar":
      return (
        <div style={{ background: "#2c2c2c", color: "#ddd", padding: "10px 16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontWeight: 700, fontSize: 12, color: "#fff" }}>{comp.label}</span>
          <div style={{ display: "flex", gap: 16 }}>
            {(comp.children || ["Home", "Features", "Settings"]).map((item, i) => (
              <span key={i} style={{ fontSize: 11, color: i === 0 ? "#fff" : "#aaa" }}>{item}</span>
            ))}
          </div>
        </div>
      );

    case "sidebar":
      return (
        <div style={{ width: 140, background: "#f0f0f0", borderRight: "1px solid #ddd", flexShrink: 0 }}>
          <div style={{ padding: "8px 10px", fontSize: 10, fontWeight: 700, color: "#888", borderBottom: "1px solid #ddd", textTransform: "uppercase", letterSpacing: 1 }}>
            {comp.label}
          </div>
          {(comp.children || []).map((item, i) => (
            <div key={i} style={{
              padding: "8px 12px",
              fontSize: 11,
              borderBottom: "1px solid #e8e8e8",
              background: i === 0 ? "#4a90d9" : "transparent",
              color: i === 0 ? "#fff" : "#555",
              cursor: "pointer",
            }}>
              {item}
            </div>
          ))}
        </div>
      );

    case "hero":
      return (
        <div style={{ background: "#e8edf2", border: "2px dashed #bbb", padding: "40px 24px", textAlign: "center" }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#555", marginBottom: 8 }}>{comp.label}</div>
          <div style={{ width: 120, height: 6, background: "#bbb", borderRadius: 3, margin: "0 auto 16px" }} />
          <div style={{ display: "inline-block", padding: "8px 24px", background: "#4a90d9", color: "#fff", borderRadius: 4, fontSize: 12 }}>
            Get Started
          </div>
        </div>
      );

    case "form":
      return (
        <div style={{ border: "1px solid #ddd", padding: 16, background: "#fafafa" }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#333", marginBottom: 12 }}>{comp.label}</div>
          {(comp.children || ["Username", "Password"]).map((field, i) => (
            <div key={i} style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 10, color: "#666", marginBottom: 3, fontWeight: 600 }}>{field}</div>
              <div style={{ height: 28, border: "1px solid #ccc", background: "#fff", borderRadius: 3 }} />
            </div>
          ))}
        </div>
      );

    case "table":
      return (
        <div style={{ border: "1px solid #ddd", overflow: "hidden" }}>
          <div style={{ display: "flex", background: "#f5f5f5", borderBottom: "2px solid #ddd" }}>
            {(comp.children || ["Column 1", "Column 2", "Column 3"]).map((col, i) => (
              <div key={i} style={{ flex: 1, padding: "6px 10px", fontSize: 10, fontWeight: 700, color: "#444", borderRight: "1px solid #ddd" }}>
                {col}
              </div>
            ))}
          </div>
          {[1, 2, 3, 4].map(row => (
            <div key={row} style={{ display: "flex", borderBottom: "1px solid #eee", background: row % 2 === 0 ? "#fafafa" : "#fff" }}>
              {(comp.children || ["", "", ""]).map((_, i) => (
                <div key={i} style={{ flex: 1, padding: "7px 10px", borderRight: "1px solid #eee" }}>
                  <div style={{ height: 8, background: "#e0e0e0", borderRadius: 2, width: `${60 + Math.random() * 30}%` }} />
                </div>
              ))}
            </div>
          ))}
        </div>
      );

    case "card_grid": {
      const count = comp.metadata?.card_count ?? 4;
      return (
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: "#555", marginBottom: 8 }}>{comp.label}</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))", gap: 10 }}>
            {Array.from({ length: count }).map((_, i) => (
              <div key={i} style={{ border: "1px solid #ddd", borderRadius: 6, padding: "12px 10px", background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
                <div style={{ height: 8, background: "#e0e0e0", borderRadius: 2, width: "60%", marginBottom: 6 }} />
                <div style={{ fontSize: 20, fontWeight: 700, color: "#4a90d9" }}>—</div>
                <div style={{ height: 6, background: "#eee", borderRadius: 2, width: "80%", marginTop: 4 }} />
              </div>
            ))}
          </div>
        </div>
      );
    }

    case "detail_view":
      return (
        <div style={{ border: "1px solid #ddd", background: "#fff", borderRadius: 4, overflow: "hidden" }}>
          <div style={{ padding: "8px 12px", background: "#f5f5f5", borderBottom: "1px solid #ddd", fontSize: 11, fontWeight: 700, color: "#333" }}>
            {comp.label}
          </div>
          {(comp.children || ["Name", "Description", "Status"]).map((field, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", padding: "8px 12px", borderBottom: "1px solid #f0f0f0" }}>
              <span style={{ width: 90, fontSize: 10, color: "#888", fontWeight: 600 }}>{field}</span>
              <div style={{ flex: 1, height: 8, background: "#e8e8e8", borderRadius: 2 }} />
            </div>
          ))}
        </div>
      );

    case "search_bar":
      return (
        <div style={{ display: "flex", gap: 8, padding: "8px 0" }}>
          <div style={{ flex: 1, height: 32, border: "1px solid #ccc", borderRadius: 4, background: "#fff", display: "flex", alignItems: "center", paddingLeft: 10 }}>
            <span style={{ fontSize: 10, color: "#aaa" }}>Search {comp.label}...</span>
          </div>
          <div style={{ height: 32, padding: "0 16px", background: "#4a90d9", color: "#fff", borderRadius: 4, display: "flex", alignItems: "center", fontSize: 11, fontWeight: 600 }}>
            Search
          </div>
        </div>
      );

    case "tabs":
      return (
        <div style={{ display: "flex", borderBottom: "2px solid #ddd" }}>
          {(comp.children || ["Overview", "Details", "Settings"]).map((tab, i) => (
            <div key={i} style={{
              padding: "8px 16px",
              fontSize: 11,
              fontWeight: 600,
              color: i === 0 ? "#4a90d9" : "#888",
              borderBottom: i === 0 ? "2px solid #4a90d9" : "2px solid transparent",
              marginBottom: -2,
              cursor: "pointer",
            }}>
              {tab}
            </div>
          ))}
        </div>
      );

    case "button_group": {
      const btnCount = comp.metadata?.button_count ?? 2;
      const labels = ["Save", "Cancel", "Delete", "Back"];
      return (
        <div style={{ display: "flex", gap: 8, padding: "4px 0" }}>
          {Array.from({ length: btnCount }).map((_, i) => (
            <div key={i} style={{
              padding: "7px 18px",
              fontSize: 11,
              fontWeight: 600,
              borderRadius: 4,
              cursor: "pointer",
              background: i === 0 ? "#4a90d9" : "#fff",
              color: i === 0 ? "#fff" : "#555",
              border: i === 0 ? "1px solid #4a90d9" : "1px solid #ccc",
            }}>
              {labels[i] || `Button ${i + 1}`}
            </div>
          ))}
        </div>
      );
    }

    case "footer":
      return (
        <div style={{ background: "#f0f0f0", borderTop: "1px solid #ddd", padding: "10px 16px", display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "auto" }}>
          <span style={{ fontSize: 10, color: "#888" }}>{comp.label}</span>
          <div style={{ display: "flex", gap: 12 }}>
            {(comp.children || ["Privacy", "Terms", "Help"]).map((item, i) => (
              <span key={i} style={{ fontSize: 10, color: "#4a90d9", textDecoration: "underline" }}>{item}</span>
            ))}
          </div>
        </div>
      );

    default:
      return (
        <div style={{ border: "2px dashed #ccc", padding: "10px 12px", background: "#f9f9f9", fontSize: 10, color: "#888" }}>
          [{comp.type}] {comp.label}
        </div>
      );
  }
}

export default function WireframeRenderer({ screen }: WireframeRendererProps) {
  const components = screen.components || [];
  const hasSidebar = components.some(c => c.type === "sidebar");
  const sidebarComp = components.find(c => c.type === "sidebar");
  const otherComps = components.filter(c => c.type !== "sidebar");

  return (
    <div style={{ fontFamily: "'Inter', -apple-system, sans-serif", border: "1px solid #ccc", borderRadius: 6, overflow: "hidden", background: "#fff", boxShadow: "0 2px 12px rgba(0,0,0,0.08)" }}>
      {/* Window chrome */}
      <div style={{ background: "#e8e8e8", padding: "6px 10px", display: "flex", alignItems: "center", gap: 6, borderBottom: "1px solid #ccc" }}>
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ff5f57" }} />
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ffbd2e" }} />
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#28c840" }} />
        <div style={{ flex: 1, marginLeft: 8, height: 18, background: "#fff", borderRadius: 3, border: "1px solid #ccc", display: "flex", alignItems: "center", paddingLeft: 8 }}>
          <span style={{ fontSize: 9, color: "#aaa" }}>localhost:3000 / {screen.screen_name?.toLowerCase().replace(/ /g, "-")}</span>
        </div>
      </div>

      {/* Screen content */}
      {hasSidebar ? (
        <div style={{ display: "flex", minHeight: 320 }}>
          {sidebarComp && <WireframeComponent comp={sidebarComp} />}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12, padding: 16 }}>
            {otherComps.map((comp, i) => (
              <WireframeComponent key={i} comp={comp} />
            ))}
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: 16 }}>
          {components.map((comp, i) => (
            <WireframeComponent key={i} comp={comp} />
          ))}
        </div>
      )}

      {screen.notes && (
        <div style={{ padding: "6px 12px", borderTop: "1px dashed #ddd", fontSize: 9, color: "#aaa", fontStyle: "italic", background: "#fafafa" }}>
          {screen.notes}
        </div>
      )}
    </div>
  );
}
