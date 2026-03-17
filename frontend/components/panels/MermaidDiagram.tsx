"use client";
import { useEffect, useRef } from "react";
import mermaid from "mermaid";

mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });

let idCounter = 0;

export default function MermaidDiagram({ chart }: { chart: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || !chart.trim()) return;
    const id = `mermaid-${++idCounter}`;
    mermaid.render(id, chart).then(({ svg }) => {
      if (ref.current) ref.current.innerHTML = svg;
    }).catch(() => {
      if (ref.current) ref.current.innerHTML = `<pre class="text-xs text-red-500 p-4 whitespace-pre-wrap">${chart}</pre>`;
    });
  }, [chart]);

  return <div ref={ref} className="w-full flex justify-center p-6" />;
}
