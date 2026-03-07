import { LayoutTemplate, ExternalLink } from "lucide-react";

export default function WireframePanel() {
  return (
    <>
      <div className="h-10 border-b border-gray-300 dark:border-[#444] flex items-center justify-between px-4 bg-gray-50 dark:bg-black flex-shrink-0 transition-colors">
        <div className="flex items-center gap-2 text-black dark:text-white">
          <LayoutTemplate size={12} />
          <span className="text-[10px] tracking-widest uppercase font-bold">UI_Mockups</span>
        </div>
        <div className="flex gap-2">
           <button className="text-[9px] border border-gray-300 dark:border-[#555] px-2 py-1 text-black dark:text-white font-bold uppercase tracking-widest hover:bg-gray-200 dark:hover:bg-white dark:hover:text-black transition-colors flex items-center gap-1">
             <ExternalLink size={10} /> Open Figma
           </button>
        </div>
      </div>

      <div className="p-6 overflow-y-auto flex-1 bg-white dark:bg-black transition-colors flex flex-col items-center justify-center">
        <div className="w-full max-w-sm border border-gray-300 dark:border-[#444] bg-gray-50 dark:bg-[#050505] p-6 shadow-sm dark:shadow-2xl transition-colors">
          <div className="h-4 border-b border-gray-300 dark:border-[#444] mb-4 flex gap-1">
            <div className="w-2 h-2 rounded-full bg-red-400 dark:bg-[#555]"></div>
            <div className="w-2 h-2 rounded-full bg-amber-400 dark:bg-[#555]"></div>
            <div className="w-2 h-2 rounded-full bg-green-400 dark:bg-[#555]"></div>
          </div>
          <div className="space-y-4">
            <div className="h-8 bg-gray-200 dark:bg-[#111] w-full transition-colors"></div>
            <div className="h-24 bg-gray-200 dark:bg-[#111] w-full transition-colors"></div>
            <div className="flex gap-4">
              <div className="h-8 bg-black dark:bg-white w-1/2 transition-colors"></div>
              <div className="h-8 bg-gray-300 dark:bg-[#333] w-1/2 transition-colors"></div>
            </div>
          </div>
        </div>
        <p className="mt-6 text-xs text-gray-500 font-mono tracking-widest uppercase">
          Generated_By: Mockup_Rendering_Agent
        </p>
      </div>
    </>
  );
}