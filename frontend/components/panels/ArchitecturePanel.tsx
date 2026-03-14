"use client";
import { useState } from "react";
import { Network, Copy } from "lucide-react";
import { useProjectStore } from "@/store/useProjectStore";

export default function ArchitecturePanel() {
  const { architecture, isLoading } = useProjectStore();
  const [copied, setCopied] = useState(false);

  const diagram: string = architecture?.system_diagram ?? "";
  const techStack: Record<string, string> = architecture?.tech_stack ?? {};
  const apiEndpoints: any[] = architecture?.api_design ?? [];
  const hasData = !!(diagram || Object.keys(techStack).length || apiEndpoints.length);

  const diagramLines = diagram ? diagram.split("\n") : [];

  const handleCopy = () => {
    if (diagram) {
      navigator.clipboard.writeText(diagram);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  return (
    <>
      <div className="h-10 border-b border-gray-300 dark:border-[#444] flex items-center justify-between px-4 bg-gray-50 dark:bg-black flex-shrink-0 transition-colors">
        <div className="flex items-center gap-2 text-black dark:text-white">
          <Network size={12} />
          <span className="text-[10px] tracking-widest uppercase font-bold text-black dark:text-white">Architecture_Graph</span>
        </div>
        {hasData && (
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              className="text-[10px] font-bold border border-gray-300 dark:border-[#555] px-2 py-1 text-gray-600 dark:text-gray-300 hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors flex items-center gap-1 bg-white dark:bg-transparent"
            >
              <Copy size={10} /> {copied ? "COPIED" : "COPY_MERMAID"}
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-auto bg-gray-100 dark:bg-[#0a0a0a] transition-colors">
        {isLoading && !hasData && (
          <div className="flex items-center justify-center h-full">
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest animate-pulse">
              -- LOADING ARCHITECTURE --
            </p>
          </div>
        )}

        {!isLoading && !hasData && (
          <div className="flex items-center justify-center h-full">
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest text-center px-8">
              -- NO ARCHITECTURE YET. RUN THE PROJECT ARCHITECT AGENT FROM THE CONSOLE --
            </p>
          </div>
        )}

        {hasData && (
          <div className="p-6 space-y-6">
            {Object.keys(techStack).length > 0 && (
              <div className="border border-gray-300 dark:border-[#555] bg-white dark:bg-[#030303] p-4">
                <h3 className="text-[10px] font-bold text-black dark:text-white uppercase tracking-widest mb-3 border-b border-gray-200 dark:border-[#333] pb-2">
                  Tech Stack
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
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
              <div className="border border-gray-300 dark:border-[#555] bg-white dark:bg-[#030303] p-4">
                <h3 className="text-[10px] font-bold text-black dark:text-white uppercase tracking-widest mb-3 border-b border-gray-200 dark:border-[#333] pb-2">
                  API Design
                </h3>
                <div className="space-y-2">
                  {apiEndpoints.map((ep: any, i: number) => (
                    <div key={i} className="flex items-start gap-3 font-mono text-xs">
                      <span className="px-2 py-0.5 bg-black dark:bg-white text-white dark:text-black text-[9px] font-bold shrink-0">
                        {ep.method}
                      </span>
                      <span className="text-black dark:text-white">{ep.path}</span>
                      <span className="text-gray-500 dark:text-gray-400 ml-auto">{ep.description}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {diagram && (
        <div className="h-36 border-t border-gray-300 dark:border-[#444] bg-gray-50 dark:bg-[#050505] p-4 text-[11px] text-gray-700 dark:text-gray-200 overflow-y-auto flex-shrink-0 font-mono transition-colors">
          {diagramLines.map((line, i) => (
            <div key={i} className="flex gap-4">
              <span className="text-black dark:text-white font-bold w-6 shrink-0 text-right">{String(i + 1).padStart(2, "0")}</span>
              <span>{line}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}