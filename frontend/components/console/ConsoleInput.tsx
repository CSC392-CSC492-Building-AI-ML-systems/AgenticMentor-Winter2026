"use client";
import { useState, KeyboardEvent, useRef, useEffect } from "react";
import { ArrowUpRight } from "lucide-react";

const AGENTS = [
  { id: "requirements", name: "Requirements Collector", color: "purple" },
  { id: "project_architect", name: "Project Architect", color: "blue" },
  { id: "execution_planner", name: "Execution Planner", color: "red" },
  { id: "mockup_rendering", name: "Mockup Rendering", color: "orange" },
  { id: "exporter", name: "Exporter Agent", color: "green" },
];

interface ConsoleInputProps {
  onSend: (text: string, agent: typeof AGENTS[0]) => void;
}

export default function ConsoleInput({ onSend }: ConsoleInputProps) {
  const [value, setValue] = useState("");
  const [selectedAgent, setSelectedAgent] = useState(AGENTS[0]);
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setShowMenu(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSend = () => {
    if (value.trim()) {
      onSend(value, selectedAgent);
      setValue("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-[#444] bg-black flex flex-col justify-end px-6 pb-6 pt-3 flex-shrink-0 relative">
      
      {/* Top Bar: Shortcuts & Target Selector */}
      <div className="flex justify-between items-end mb-3">
        {/* Command Shortcuts */}
        <div className="flex gap-4 text-[11px] text-gray-200 font-medium">
          <button className="hover:text-white transition-colors flex items-center gap-1.5" onClick={() => setValue("/sequence ")}>
            <span className="text-white text-[8px]">●</span> /sequence
          </button>
          <button className="hover:text-white transition-colors flex items-center gap-1.5" onClick={() => setValue("/wireframe ")}>
            <span className="text-white text-[8px]">●</span> /wireframe
          </button>
        </div>

        {/* Agent Target Selector */}
        <div className="relative" ref={menuRef}>
          <span className="text-[10px] text-gray-200 font-bold uppercase tracking-widest mr-2">Target_Engine:</span>
          <button 
            onClick={() => setShowMenu(!showMenu)}
            className="text-[10px] text-white font-bold uppercase tracking-widest border-b border-dashed border-gray-400 hover:text-gray-200 hover:border-white transition-colors"
          >
            [{selectedAgent.name}]
          </button>

          {showMenu && (
            <div className="absolute bottom-full right-0 mb-2 w-56 bg-black border border-[#555] shadow-2xl z-50 py-1">
              <div className="px-3 py-2 text-[9px] font-bold text-gray-200 uppercase tracking-widest border-b border-[#444]">
                Select_Routing_Node
              </div>
              {AGENTS.map((agent) => (
                <button
                  key={agent.id}
                  onClick={() => { setSelectedAgent(agent); setShowMenu(false); }}
                  className="w-full text-left px-3 py-2 text-[10px] font-bold text-gray-200 hover:bg-white hover:text-black transition-colors uppercase tracking-widest"
                >
                  &gt; {agent.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Input Field */}
      <div className="border border-[#555] flex items-stretch focus-within:border-white transition-colors bg-[#050505]">
        <div className="px-4 flex items-center justify-center text-white font-bold border-r border-[#555]">&gt;_</div>
        
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Execute prompt for ${selectedAgent.name}...`}
          className="flex-1 bg-transparent border-none text-sm text-white placeholder:text-gray-400 px-4 py-4 focus:outline-none font-mono"
        />
        
        <div className="flex items-stretch border-l border-[#555]">
          <div className="flex flex-col justify-center px-4 text-right">
            <span className="text-[10px] font-bold text-white uppercase tracking-widest">Engine:01</span>
            <span className="text-[8px] text-gray-200 tracking-widest">READY</span>
          </div>
          <button 
            onClick={handleSend}
            disabled={!value.trim()}
            className="bg-white text-black px-4 flex items-center justify-center hover:bg-gray-300 transition-colors disabled:opacity-50"
          >
            <ArrowUpRight size={18} strokeWidth={3} />
          </button>
        </div>
      </div>
    </div>
  );
}