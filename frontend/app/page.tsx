import Link from "next/link";
import { Terminal, ShieldAlert, ChevronRight } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-black text-white font-mono selection:bg-gray-700 selection:text-white relative overflow-hidden">
      
      {/* Background Grid/Decorations */}
      <div className="absolute top-0 left-0 w-full h-full bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:50px_50px] pointer-events-none opacity-20"></div>

      {/* Main Content Terminal */}
      <div className="z-10 w-full max-w-2xl px-6 flex flex-col items-center">
        
        {/* System Status Header */}
        <div className="mb-12 flex flex-col items-center">
          <Terminal size={48} className="text-gray-400 mb-6" strokeWidth={1} />
          <div className="flex items-center gap-3 border border-[#333] bg-[#050505] px-4 py-2">
            <div className="w-2 h-2 bg-white rounded-full animate-pulse shadow-[0_0_8px_rgba(255,255,255,0.8)]"></div>
            <span className="text-[10px] text-gray-300 tracking-widest uppercase font-bold">System Status: Online</span>
            <span className="text-[10px] text-gray-600 border-l border-[#333] pl-3 ml-1">V_4.0.1</span>
          </div>
        </div>

        {/* Title Block */}
        <div className="text-center space-y-6 mb-16 w-full">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tighter uppercase text-white">
            Agentic_Project<br/>Mentor
          </h1>
          
          <div className="border-l-2 border-[#444] pl-4 max-w-lg mx-auto text-left space-y-2">
            <p className="text-gray-400 text-sm flex gap-2">
              <span className="text-gray-600 font-bold">&gt;_</span>
              Transform unstructured ideas into architect-level system designs.
            </p>
            <p className="text-gray-400 text-sm flex gap-2">
              <span className="text-gray-600 font-bold">&gt;_</span>
              Multi-agent orchestration protocol ready for execution.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
          
          {/* Login Action */}
          <Link
            href="/login"
            className="flex-1 sm:max-w-[220px] border border-[#444] bg-[#050505] hover:border-white transition-all p-4 flex flex-col items-start group relative"
          >
            {/* Targeting Corners */}
            <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-white opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-white opacity-0 group-hover:opacity-100 transition-opacity"></div>
            
            <ShieldAlert size={14} className="text-gray-500 mb-3 group-hover:text-white transition-colors" />
            <span className="text-[10px] text-gray-500 tracking-widest uppercase mb-1 font-bold">Req_Access</span>
            <span className="text-sm font-bold text-white uppercase tracking-widest">Authenticate</span>
          </Link>

          {/* Direct Dashboard Access (Bypass) */}
          <Link
            href="/dashboard"
            className="flex-1 sm:max-w-[220px] border border-white bg-white text-black hover:bg-gray-200 transition-all p-4 flex flex-col items-start group"
          >
            <ChevronRight size={14} className="text-black mb-3 group-hover:translate-x-1 transition-transform" />
            <span className="text-[10px] text-gray-600 tracking-widest uppercase mb-1 font-bold">System_Bypass</span>
            <span className="text-sm font-bold uppercase tracking-widest">Init_Dashboard</span>
          </Link>

        </div>

      </div>

      {/* Footer System Log */}
      <div className="absolute bottom-4 left-4 text-[9px] text-gray-600 space-y-1 opacity-50 hidden sm:block">
        <p>14:02:11 -- INIT SEQUENCE STARTED</p>
        <p>14:02:12 -- LOADING ORCHESTRATOR_MODULE</p>
        <p>14:02:12 -- WAITING FOR USER INPUT...</p>
      </div>
    </div>
  );
}