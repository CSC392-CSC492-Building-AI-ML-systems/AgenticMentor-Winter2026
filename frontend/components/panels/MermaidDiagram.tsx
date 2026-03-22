"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import mermaid from "mermaid";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });

let idCounter = 0;

export default function MermaidDiagram({ chart }: { chart: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, y: 0 });
  const offsetStart = useRef({ x: 0, y: 0 });

  useEffect(() => {
    if (!ref.current || !chart.trim()) return;
    const id = `mermaid-${++idCounter}`;
    mermaid.render(id, chart).then(({ svg }) => {
      if (ref.current) ref.current.innerHTML = svg;
    }).catch(() => {
      if (ref.current) ref.current.innerHTML = `<pre class="text-xs text-red-500 p-4 whitespace-pre-wrap">${chart}</pre>`;
    });
  }, [chart]);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setScale(s => Math.min(3, Math.max(0.2, s + delta)));
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    isPanning.current = true;
    panStart.current = { x: e.clientX, y: e.clientY };
    offsetStart.current = { ...offset };
    containerRef.current!.style.cursor = "grabbing";
  }, [offset]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isPanning.current) return;
    setOffset({
      x: offsetStart.current.x + (e.clientX - panStart.current.x),
      y: offsetStart.current.y + (e.clientY - panStart.current.y),
    });
  }, []);

  const handleMouseUp = useCallback(() => {
    isPanning.current = false;
    if (containerRef.current) containerRef.current.style.cursor = "grab";
  }, []);

  const reset = () => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  };

  return (
    <div className="relative w-full h-full flex flex-col">
      {/* Zoom controls */}
      <div className="absolute top-3 right-3 z-10 flex items-center gap-1 bg-white dark:bg-[#111] border border-gray-200 dark:border-[#333] shadow-sm">
        <button
          onClick={() => setScale(s => Math.min(3, +(s + 0.2).toFixed(1)))}
          className="p-1.5 text-gray-500 hover:text-black dark:hover:text-white transition-colors"
          title="Zoom in"
        >
          <ZoomIn size={13} />
        </button>
        <span className="text-[10px] font-mono text-gray-500 dark:text-gray-400 w-10 text-center select-none">
          {Math.round(scale * 100)}%
        </span>
        <button
          onClick={() => setScale(s => Math.max(0.2, +(s - 0.2).toFixed(1)))}
          className="p-1.5 text-gray-500 hover:text-black dark:hover:text-white transition-colors"
          title="Zoom out"
        >
          <ZoomOut size={13} />
        </button>
        <div className="w-px h-4 bg-gray-200 dark:bg-[#333]" />
        <button
          onClick={reset}
          className="p-1.5 text-gray-500 hover:text-black dark:hover:text-white transition-colors"
          title="Reset view"
        >
          <Maximize2 size={13} />
        </button>
      </div>

      {/* Pannable/zoomable canvas */}
      <div
        ref={containerRef}
        className="flex-1 overflow-hidden select-none"
        style={{ cursor: "grab" }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <div
          style={{
            transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
            transformOrigin: "center center",
            transition: isPanning.current ? "none" : "transform 0.1s ease",
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
          }}
        >
          <div ref={ref} className="w-full flex justify-center" />
        </div>
      </div>
    </div>
  );
}
