"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import mermaid from "mermaid";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

let idCounter = 0;

export default function MermaidDiagram({ chart }: { chart: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, y: 0 });
  const offsetStart = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const root = document.documentElement;
    const syncTheme = () => setIsDarkMode(root.classList.contains("dark"));
    syncTheme();
    const observer = new MutationObserver(syncTheme);
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!ref.current || !chart.trim()) return;
    mermaid.initialize({
      startOnLoad: false,
      theme: isDarkMode ? "dark" : "default",
      securityLevel: "loose",
    });
    const id = `mermaid-${++idCounter}`;
    mermaid.render(id, chart).then(({ svg }) => {
      if (ref.current) ref.current.innerHTML = svg;
    }).catch(() => {
      if (ref.current) ref.current.innerHTML = `<pre class="text-xs text-red-500 p-4 whitespace-pre-wrap">${chart}</pre>`;
    });
  }, [chart, isDarkMode]);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setScale(s => Math.min(3, Math.max(0.2, s + delta)));
  }, []);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    isPanning.current = true;
    panStart.current = { x: e.clientX, y: e.clientY };
    offsetStart.current = { ...offset };
    if (containerRef.current) {
      containerRef.current.style.cursor = "grabbing";
      containerRef.current.setPointerCapture(e.pointerId);
    }
  }, [offset]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!isPanning.current) return;
    setOffset({
      x: offsetStart.current.x + (e.clientX - panStart.current.x),
      y: offsetStart.current.y + (e.clientY - panStart.current.y),
    });
  }, []);

  const handlePointerUp = useCallback((e: React.PointerEvent) => {
    isPanning.current = false;
    if (containerRef.current) {
      containerRef.current.style.cursor = "grab";
      if (containerRef.current.hasPointerCapture(e.pointerId)) {
        containerRef.current.releasePointerCapture(e.pointerId);
      }
    }
  }, []);

  const reset = () => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  };

  return (
    <div className="relative w-full h-full flex flex-col">
      {/* Zoom controls */}
      <div className="absolute top-2 right-2 sm:top-3 sm:right-3 z-10 flex items-center gap-1 bg-white dark:bg-[#111] border border-gray-200 dark:border-[#333] shadow-sm">
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
        className="flex-1 overflow-hidden select-none touch-none"
        style={{ cursor: "grab", touchAction: "none" }}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
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
