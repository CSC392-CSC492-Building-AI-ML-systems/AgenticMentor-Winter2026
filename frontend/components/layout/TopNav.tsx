import { Terminal, Settings, User } from "lucide-react";

export default function TopNav() {
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
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-white rounded-full animate-pulse shadow-[0_0_8px_rgba(255,255,255,1)]"></div>
          <span className="text-[10px] text-white tracking-widest uppercase font-bold">System Ready</span>
        </div>
        
        <div className="w-[1px] h-4 bg-[#555]"></div>

        <button className="text-gray-200 hover:text-white transition-colors">
          <Settings size={14} />
        </button>
        <div className="w-6 h-6 bg-[#111] flex items-center justify-center border border-[#555]">
          <User size={14} className="text-white" />
        </div>
      </div>
    </div>
  );
}