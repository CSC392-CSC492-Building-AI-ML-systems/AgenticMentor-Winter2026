"use client";
import { useState } from "react";
import { LayoutTemplate } from "lucide-react";
import { useProjectStore } from "@/store/useProjectStore";
import WireframeRenderer from "./WireframeRenderer";

export default function WireframePanel() {
  const { mockups, isLoading } = useProjectStore();
  const [selected, setSelected] = useState(0);

  const hasData = mockups.length > 0;
  const current = mockups[selected];

  // Parse wireframe_spec from the mockup entry
  const getSpec = (mockup: any) => {
    if (mockup?.wireframe_spec && typeof mockup.wireframe_spec === "object") {
      return mockup.wireframe_spec;
    }
    return null;
  };

  const spec = current ? getSpec(current) : null;

  return (
    <>
      <div className="h-10 border-b border-gray-300 dark:border-[#444] flex items-center justify-between px-3 sm:px-4 bg-gray-50 dark:bg-black shrink-0 transition-colors">
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

      <div className="flex-1 overflow-hidden flex flex-col lg:flex-row bg-white dark:bg-black transition-colors">
        {/* Sidebar: screen list */}
        {hasData && mockups.length > 1 && (
          <div className="w-full lg:w-48 border-b lg:border-b-0 lg:border-r border-gray-200 dark:border-[#333] overflow-x-auto lg:overflow-y-auto flex lg:block shrink-0">
            {mockups.map((m: any, i: number) => (
              <button
                key={i}
                onClick={() => setSelected(i)}
                className={`shrink-0 lg:w-full text-left px-3 py-2.5 text-[10px] font-bold uppercase tracking-widest border-r lg:border-r-0 lg:border-b border-gray-100 dark:border-[#222] transition-colors
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

        <div className="flex-1 overflow-y-auto p-3 sm:p-6 flex items-start justify-center">
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

          {hasData && current && spec && (
            <div className="w-full max-w-5xl mx-auto">
              <div className="w-full min-h-[380px] h-[min(72vh,900px)] overflow-hidden border border-gray-200 dark:border-[#333]">
                <WireframeRenderer screen={spec} />
              </div>
            </div>
          )}

          {hasData && current && !spec && (
            <div className="space-y-3">
              <h2 className="text-sm font-bold text-black dark:text-white uppercase tracking-widest">
                {current.screen_name ?? current.screen_id ?? `Screen ${selected + 1}`}
              </h2>
              {current.wireframe_code && (
                <pre className="text-[9px] font-mono text-gray-600 dark:text-gray-400 whitespace-pre-wrap overflow-auto border border-dashed border-gray-200 dark:border-[#333] p-3">
                  {typeof current.wireframe_code === "string"
                    ? current.wireframe_code
                    : JSON.stringify(current.wireframe_code, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>

      {hasData && (
        <div className="h-6 border-t border-gray-200 dark:border-[#333] flex items-center px-4 bg-gray-50 dark:bg-[#050505] shrink-0">
          <span className="text-[9px] text-gray-500 font-mono tracking-widest uppercase">
            Generated_By: Mockup_Rendering_Agent
          </span>
        </div>
      )}
    </>
  );
}
