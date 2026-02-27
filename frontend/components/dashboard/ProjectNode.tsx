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
    <div className="border border-gray-300 dark:border-[#444] bg-white dark:bg-black hover:bg-gray-50 dark:hover:bg-[#111] hover:border-black dark:hover:border-white transition-all p-5 flex flex-col group relative cursor-pointer h-full">
      
      {/* Corner Accents - Now swap between Black and White */}
      <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-black dark:border-white opacity-0 group-hover:opacity-100 transition-opacity"></div>
      <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-black dark:border-white opacity-0 group-hover:opacity-100 transition-opacity"></div>
      <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-black dark:border-white opacity-0 group-hover:opacity-100 transition-opacity"></div>
      <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-black dark:border-white opacity-0 group-hover:opacity-100 transition-opacity"></div>

      {/* Header Info */}
      <div className="flex justify-between items-start mb-6">
        <div className="flex flex-col">
          <span className="text-[10px] text-gray-500 dark:text-gray-200 font-mono tracking-widest uppercase mb-1 transition-colors">NODE_ID</span>
          <span className="text-xs text-black dark:text-white font-mono font-bold tracking-wider transition-colors">{id}</span>
        </div>
        
        <div className="flex items-center gap-2 border border-gray-300 dark:border-[#444] px-2 py-1 bg-gray-50 dark:bg-[#050505] transition-colors">
          <div className={`w-1.5 h-1.5 rounded-full ${
            status === "ONLINE" ? "bg-black dark:bg-white animate-pulse" : 
            status === "BUILDING" ? "bg-gray-400 dark:bg-gray-300" : "bg-gray-300 dark:bg-[#555]"
          }`}></div>
          <span className="text-[9px] font-bold text-black dark:text-white tracking-widest uppercase transition-colors">{status}</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="mb-6 flex-1">
        <h3 className="text-lg font-bold text-black dark:text-white mb-2 tracking-tight transition-colors">{name}</h3>
        <p className="text-xs text-gray-700 dark:text-gray-200 leading-relaxed font-mono transition-colors">
          {description}
        </p>
      </div>

      {/* Footer / Metadata */}
      <div className="mt-auto border-t border-gray-300 dark:border-[#444] pt-4 flex flex-col gap-4 transition-colors">
        
        <div className="flex flex-wrap gap-2">
          {techStack.map((tech, i) => (
            <span key={i} className="text-[9px] text-black dark:text-white border border-gray-300 dark:border-[#555] px-1.5 py-0.5 uppercase tracking-widest flex items-center gap-1 transition-colors">
              <Cpu size={10} />
              {tech}
            </span>
          ))}
        </div>

        <div className="flex justify-between items-center text-[10px] text-gray-500 dark:text-gray-200 font-mono transition-colors">
          <div className="flex items-center gap-1.5 text-black dark:text-white transition-colors">
            <Clock size={10} />
            <span>SYNC: {lastSync}</span>
          </div>
          <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity text-black dark:text-white font-bold">
            <span>CONNECT</span>
            <Activity size={10} />
          </div>
        </div>

      </div>
    </div>
  );
}