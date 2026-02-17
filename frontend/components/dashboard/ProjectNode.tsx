import { Activity, Cpu, Clock } from "lucide-react";

interface ProjectNodeProps {
  id: string;
  name: string;
  description: string;
  status: "ONLINE" | "IDLE" | "BUILDING";
  lastSync: string;
  techStack: string[];
}

export default function ProjectNode({ id, name, description, status, lastSync, techStack }: ProjectNodeProps) {
  return (
    <div className="border border-[#444] bg-black hover:bg-[#111] hover:border-white transition-all p-5 flex flex-col group relative cursor-pointer h-full">
      
      {/* Corner Accents */}
      <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-white opacity-0 group-hover:opacity-100 transition-opacity"></div>
      <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-white opacity-0 group-hover:opacity-100 transition-opacity"></div>
      <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-white opacity-0 group-hover:opacity-100 transition-opacity"></div>
      <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-white opacity-0 group-hover:opacity-100 transition-opacity"></div>

      {/* Header Info */}
      <div className="flex justify-between items-start mb-6">
        <div className="flex flex-col">
          <span className="text-[10px] text-gray-200 font-mono tracking-widest uppercase mb-1">NODE_ID</span>
          <span className="text-xs text-white font-mono font-bold tracking-wider">{id}</span>
        </div>
        
        <div className="flex items-center gap-2 border border-[#444] px-2 py-1 bg-[#050505]">
          <div className={`w-1.5 h-1.5 rounded-full ${
            status === "ONLINE" ? "bg-white animate-pulse" : 
            status === "BUILDING" ? "bg-gray-300" : "bg-[#555]"
          }`}></div>
          <span className="text-[9px] font-bold text-white tracking-widest uppercase">{status}</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="mb-6 flex-1">
        <h3 className="text-lg font-bold text-white mb-2 tracking-tight">{name}</h3>
        <p className="text-xs text-gray-200 leading-relaxed font-mono">
          {description}
        </p>
      </div>

      {/* Footer / Metadata */}
      <div className="mt-auto border-t border-[#444] pt-4 flex flex-col gap-4">
        
        <div className="flex flex-wrap gap-2">
          {techStack.map((tech, i) => (
            <span key={i} className="text-[9px] text-white border border-[#555] px-1.5 py-0.5 uppercase tracking-widest flex items-center gap-1">
              <Cpu size={10} />
              {tech}
            </span>
          ))}
        </div>

        <div className="flex justify-between items-center text-[10px] text-gray-200 font-mono">
          <div className="flex items-center gap-1.5 text-white">
            <Clock size={10} />
            <span>SYNC: {lastSync}</span>
          </div>
          <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity text-white font-bold">
            <span>CONNECT</span>
            <Activity size={10} />
          </div>
        </div>

      </div>
    </div>
  );
}