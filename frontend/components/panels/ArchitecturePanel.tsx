"use client";
import { useState, useRef } from "react";
import { Network, Copy } from "lucide-react";
import { useProjectStore } from "@/store/useProjectStore";
import MermaidDiagram from "./MermaidDiagram";

export default function ArchitecturePanel() {
  const { architecture, isLoading } = useProjectStore();
  const [copied, setCopied] = useState(false);
  const [leftWidth, setLeftWidth] = useState(320);
  const [activeDiagram, setActiveDiagram] = useState<"system" | "erd">("system");
  const isDragging = useRef(false);

  const startResize = (e: React.MouseEvent) => {
    isDragging.current = true;
    document.body.style.cursor = "ew-resize";
    document.body.style.userSelect = "none";

    const panelEl = (e.currentTarget as HTMLElement).closest<HTMLElement>("[data-arch-panel]");
    const panelLeft = panelEl?.getBoundingClientRect().left ?? 0;

    const onMove = (ev: MouseEvent) => {
      if (!isDragging.current) return;
      const newWidth = ev.clientX - panelLeft;
      setLeftWidth(Math.max(200, Math.min(newWidth, window.innerWidth * 0.6)));
    };

    const onUp = () => {
      isDragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  };

  const diagram: string = architecture?.system_diagram ?? "";
  const erdDiagram: string = architecture?.data_schema ?? "";
  const techStack: Record<string, string> = architecture?.tech_stack ?? {};
  const apiEndpoints: any[] = architecture?.api_design ?? [];
  const hasData = !!(
    diagram ||
    erdDiagram ||
    Object.keys(techStack).length ||
    apiEndpoints.length
  );
  const visibleDiagram = activeDiagram === "system" ? diagram : erdDiagram;

  const handleCopy = () => {
    const contentToCopy = activeDiagram === "system" ? diagram : erdDiagram;
    if (contentToCopy) {
      navigator.clipboard.writeText(contentToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  const showSystemTab = !!diagram;
  const showErdTab = !!erdDiagram;

  return (
    <div data-arch-panel className="flex flex-col h-full">
      {/* Header */}
      <div className="h-10 border-b border-gray-300 dark:border-[#444] flex items-center justify-between px-4 bg-gray-50 dark:bg-black shrink-0 transition-colors">
        <div className="flex items-center gap-2 text-black dark:text-white">
          <Network size={12} />
          <span className="text-[10px] tracking-widest uppercase font-bold">Architecture_Graph</span>
        </div>
        {hasData && (showSystemTab || showErdTab) && (
          <button
            onClick={handleCopy}
            className="text-[10px] font-bold border border-gray-300 dark:border-[#555] px-2 py-1 text-gray-600 dark:text-gray-300 hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors flex items-center gap-1 bg-white dark:bg-transparent"
          >
            <Copy size={10} /> {copied ? "COPIED" : `COPY_${activeDiagram.toUpperCase()}_DIAGRAM`}
          </button>
        )}
      </div>

      {/* Empty states */}
      {isLoading && !hasData && (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest animate-pulse">
            -- LOADING ARCHITECTURE --
          </p>
        </div>
      )}
      {!isLoading && !hasData && (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest text-center px-8">
            -- NO ARCHITECTURE YET. RUN THE PROJECT ARCHITECT AGENT FROM THE CONSOLE --
          </p>
        </div>
      )}

      {/* Side-by-side layout */}
      {hasData && (
        <div className="flex-1 flex overflow-hidden">

          {/* Left: Tech Stack + API Design */}
          <div
            style={{ width: `${leftWidth}px` }}
            className="shrink-0 overflow-y-auto bg-gray-100 dark:bg-[#0a0a0a] transition-colors"
          >
            <div className="p-5 space-y-5">
              {Object.keys(techStack).length > 0 && (
                <div className="border border-gray-300 dark:border-[#333] bg-white dark:bg-[#030303] p-4">
                  <h3 className="text-[10px] font-bold text-black dark:text-white uppercase tracking-widest mb-3 border-b border-gray-200 dark:border-[#222] pb-2">
                    Tech Stack
                  </h3>
                  <div className="grid grid-cols-1 gap-3">
                    {Object.entries(techStack).map(([layer, tech]) => (
                      <div key={layer} className="text-xs font-mono">
                        <span className="text-gray-500 dark:text-gray-400 block text-[10px] uppercase">{layer}</span>
                        <span className="text-black dark:text-white font-bold">{tech}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {apiEndpoints.length > 0 && (
                <div className="border border-gray-300 dark:border-[#333] bg-white dark:bg-[#030303] p-4">
                  <h3 className="text-[10px] font-bold text-black dark:text-white uppercase tracking-widest mb-3 border-b border-gray-200 dark:border-[#222] pb-2">
                    API Design
                  </h3>
                  <div className="space-y-2">
                    {apiEndpoints.map((ep: any, i: number) => (
                      <div key={i} className="flex flex-col gap-0.5 font-mono text-xs border-b border-gray-100 dark:border-[#1a1a1a] pb-2 last:border-0 last:pb-0">
                        <div className="flex items-center gap-2">
                          <span className="px-1.5 py-0.5 bg-black dark:bg-white text-white dark:text-black text-[9px] font-bold shrink-0">
                            {ep.method}
                          </span>
                          <span className="text-black dark:text-white">{ep.path}</span>
                        </div>
                        {ep.description && (
                          <span className="text-gray-500 dark:text-gray-400 text-[10px] pl-1">{ep.description}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </div>
          </div>

          {/* Drag handle */}
          <div
            onMouseDown={startResize}
            className="w-1.5 shrink-0 cursor-ew-resize bg-gray-200 dark:bg-[#222] hover:bg-black dark:hover:bg-white transition-colors z-10"
            title="Drag to resize"
          />

          {/* Right: Mermaid diagram */}
          <div className="flex-1 overflow-auto bg-white dark:bg-[#050505] transition-colors">
            {showSystemTab || showErdTab ? (
              <>
                <div className="px-4 py-2 border-b border-gray-200 dark:border-[#222] flex items-center justify-between gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500">Architecture_Diagrams</span>
                  <div className="flex items-center gap-2">
                    {showSystemTab && (
                      <button
                        onClick={() => setActiveDiagram("system")}
                        className={`text-[9px] px-2 py-1 border uppercase tracking-widest font-bold transition-colors ${
                          activeDiagram === "system"
                            ? "border-black dark:border-white bg-black dark:bg-white text-white dark:text-black"
                            : "border-gray-300 dark:border-[#555] text-gray-600 dark:text-gray-300 hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black"
                        }`}
                      >
                        System
                      </button>
                    )}
                    {showErdTab && (
                      <button
                        onClick={() => setActiveDiagram("erd")}
                        className={`text-[9px] px-2 py-1 border uppercase tracking-widest font-bold transition-colors ${
                          activeDiagram === "erd"
                            ? "border-black dark:border-white bg-black dark:bg-white text-white dark:text-black"
                            : "border-gray-300 dark:border-[#555] text-gray-600 dark:text-gray-300 hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black"
                        }`}
                      >
                        ERD
                      </button>
                    )}
                  </div>
                </div>
                {visibleDiagram ? <MermaidDiagram chart={visibleDiagram} /> : (
                  <div className="flex items-center justify-center h-full">
                    <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Selected diagram not available</p>
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">No diagram generated</p>
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  );
}
