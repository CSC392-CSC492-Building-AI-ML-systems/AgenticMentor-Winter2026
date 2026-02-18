"use client";
import { useState, useRef, useEffect } from "react";
import { Terminal, Settings, User, Download, FileText, Github, FileDown } from "lucide-react";

export default function TopNav() {
  const [showExport, setShowExport] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(event.target as Node)) setShowExport(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="h-12 border-b border-[#444] flex items-center justify-between px-6 bg-black flex-shrink-0">
      <div className="flex items-center gap-4">
        <Terminal size={16} className="text-white" />
        <span className="text-xs font-bold tracking-widest text-white uppercase">
          Command_Center
        </span>
        <span className="text-[10px] text-gray-200 font-bold">V4.0.1</span>
      </div>

      <div className="flex items-center gap-6">
        
        {/* EXPORTER AGENT ACTION MENU */}
        <div className="relative" ref={exportRef}>
          <button 
            onClick={() => setShowExport(!showExport)}
            className="flex items-center gap-2 border border-[#555] bg-[#050505] hover:border-white text-white px-3 py-1 text-[10px] font-bold tracking-widest uppercase transition-colors"
          >
            <Download size={12} />
            Init_Exporter
          </button>

          {showExport && (
            <div className="absolute top-full right-0 mt-2 w-56 bg-black border border-[#555] shadow-2xl z-50 py-1">
              <div className="px-3 py-2 text-[9px] font-bold text-gray-400 uppercase tracking-widest border-b border-[#444]">
                Select_Export_Medium
              </div>
              <button className="w-full flex items-center gap-3 px-3 py-2.5 text-[10px] font-bold text-gray-200 hover:bg-white hover:text-black transition-colors uppercase tracking-widest">
                <FileDown size={14} /> Consolidate PDF
              </button>
              <button className="w-full flex items-center gap-3 px-3 py-2.5 text-[10px] font-bold text-gray-200 hover:bg-white hover:text-black transition-colors uppercase tracking-widest">
                <Github size={14} /> Push to GitHub README
              </button>
              <button className="w-full flex items-center gap-3 px-3 py-2.5 text-[10px] font-bold text-gray-200 hover:bg-white hover:text-black transition-colors uppercase tracking-widest">
                <FileText size={14} /> Raw Markdown
              </button>
            </div>
          )}
        </div>

        <div className="w-[1px] h-4 bg-[#555]"></div>

        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-white rounded-full animate-pulse shadow-[0_0_8px_rgba(255,255,255,1)]"></div>
          <span className="text-[10px] text-white tracking-widest uppercase font-bold">System Ready</span>
        </div>
        
        <div className="w-[1px] h-4 bg-[#555]"></div>

        <button className="text-gray-200 hover:text-white transition-colors">
          <Settings size={14} />
        </button>
        <div className="w-6 h-6 bg-[#111] flex items-center justify-center border border-[#555] cursor-pointer hover:border-white transition-colors">
          <User size={14} className="text-white" />
        </div>
      </div>
    </div>
  );
}