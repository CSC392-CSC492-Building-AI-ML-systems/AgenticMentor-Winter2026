"use client";
import { useState } from "react";
import { LayoutTemplate } from "lucide-react";
import { useProjectStore } from "@/store/useProjectStore";

export default function WireframePanel() {
  const { mockups, isLoading } = useProjectStore();
  const [selected, setSelected] = useState(0);

  const hasData = mockups.length > 0;
  const current = mockups[selected];

  return (
    <>
      <div className="h-10 border-b border-gray-300 dark:border-[#444] flex items-center justify-between px-4 bg-gray-50 dark:bg-black flex-shrink-0 transition-colors">
        <div className="flex items-center gap-2 text-black dark:text-white">
          <LayoutTemplate size={12} />
          <span className="text-[10px] tracking-widest uppercase font-bold">UI_Mockups</span>
        </div>
        {hasData && (
          <span className="text-[9px] border border-gray-300 dark:border-[#555] bg-white dark:bg-[#111] px-2 py-1 text-gray-600 dark:text-gray-300 font-bold uppercase tracking-widest transition-colors">
            {mockups.length} Screen{mockups.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-hidden flex bg-white dark:bg-black transition-colors">
        {/* Sidebar: screen list */}
        {hasData && mockups.length > 1 && (
          <div className="w-48 border-r border-gray-200 dark:border-[#333] overflow-y-auto flex-shrink-0">
            {mockups.map((m: any, i: number) => (
              <button
                key={i}
                onClick={() => setSelected(i)}
                className={`w-full text-left px-3 py-3 text-[10px] font-bold uppercase tracking-widest border-b border-gray-100 dark:border-[#222] transition-colors
                  ${selected === i
                    ? "bg-black dark:bg-white text-white dark:text-black"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-[#111]"
                  }`}
              >
                {m.screen_name ?? m.screen_id ?? `Screen ${i + 1}`}
              </button>
            ))}
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-6">
          {isLoading && !hasData && (
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest animate-pulse">
              -- LOADING MOCKUPS --
            </p>
          )}

          {!isLoading && !hasData && (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest text-center">
                -- NO MOCKUPS YET. RUN THE MOCKUP AGENT FROM THE CONSOLE --
              </p>
            </div>
          )}

          {hasData && current && (
            <div className="space-y-4">
              <h2 className="text-sm font-bold text-black dark:text-white uppercase tracking-widest">
                {current.screen_name ?? current.screen_id ?? `Screen ${selected + 1}`}
              </h2>

              {current.user_flow && (
                <p className="text-xs font-mono text-gray-600 dark:text-gray-400">{current.user_flow}</p>
              )}

              {current.wireframe_code && (
                <div className="border border-gray-200 dark:border-[#333] bg-gray-50 dark:bg-[#050505] p-4">
                  <h3 className="text-[10px] font-bold text-black dark:text-white uppercase tracking-widest mb-2">Wireframe Code</h3>
                  <pre className="text-[10px] font-mono text-gray-700 dark:text-gray-300 whitespace-pre-wrap overflow-auto max-h-64">
                    {typeof current.wireframe_code === "string"
                      ? current.wireframe_code
                      : JSON.stringify(current.wireframe_code, null, 2)}
                  </pre>
                </div>
              )}

              {current.interactions?.length > 0 && (
                <div className="border border-gray-200 dark:border-[#333] bg-gray-50 dark:bg-[#050505] p-4">
                  <h3 className="text-[10px] font-bold text-black dark:text-white uppercase tracking-widest mb-2">Interactions</h3>
                  <ul className="space-y-1 text-xs font-mono text-gray-700 dark:text-gray-300">
                    {current.interactions.map((ix: string, i: number) => (
                      <li key={i}>&gt; {ix}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {hasData && (
        <div className="h-6 border-t border-gray-200 dark:border-[#333] flex items-center px-4 bg-gray-50 dark:bg-[#050505] flex-shrink-0">
          <span className="text-[9px] text-gray-500 font-mono tracking-widest uppercase">
            Generated_By: Mockup_Rendering_Agent
          </span>
        </div>
      )}
    </>
  );
}