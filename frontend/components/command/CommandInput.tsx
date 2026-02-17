"use client";
import { useState } from "react";
import { ArrowUpRight } from "lucide-react";

export default function CommandInput() {
  const [value, setValue] = useState("");

  return (
    <div className="h-32 border-t border-[#333] bg-black flex flex-col justify-end px-6 pb-6 pt-2 flex-shrink-0">
      
      <div className="flex gap-4 text-[11px] text-gray-200 mb-3 px-2 font-medium">
        <button className="hover:text-white transition-colors flex items-center gap-1.5">
          <span className="text-white text-[8px]">●</span> /sequence
        </button>
        <button className="hover:text-white transition-colors flex items-center gap-1.5">
          <span className="text-white text-[8px]">●</span> /wireframe
        </button>
        <button className="hover:text-white transition-colors flex items-center gap-1.5">
          <span className="text-white text-[8px]">●</span> /refactor
        </button>
      </div>

      <div className="border border-[#555] flex items-stretch focus-within:border-white transition-colors bg-[#050505]">
        <div className="px-4 flex items-center justify-center text-white font-bold border-r border-[#555]">
          &gt;_
        </div>
        
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Execute prompt (e.g., /sequence Generate auth flow diagrams)"
          className="flex-1 bg-transparent border-none text-sm text-white placeholder:text-gray-300 px-4 py-4 focus:outline-none font-mono"
        />
        
        <div className="flex items-stretch border-l border-[#555]">
          <div className="flex flex-col justify-center px-4 text-right">
            <span className="text-[10px] font-bold text-white uppercase tracking-widest">Engine:01</span>
            <span className="text-[8px] text-gray-200 tracking-widest">READY</span>
          </div>
          <button className="bg-white text-black px-4 flex items-center justify-center hover:bg-gray-300 transition-colors">
            <ArrowUpRight size={18} strokeWidth={3} />
          </button>
        </div>
      </div>
    </div>
  );
}