import Link from "next/link";
import { Terminal, ShieldAlert, ChevronRight } from "lucide-react";
import ThemeToggle from "@/components/layout/ThemeToggle";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-white dark:bg-black text-black dark:text-white font-mono selection:bg-gray-300 dark:selection:bg-gray-200 selection:text-black relative overflow-hidden transition-colors">
      /* Theme Toggle Button - Inverts icon color on theme swap */
      <div className="absolute top-6 right-6 z-50">
        <ThemeToggle />
      </div>

      {/* Background Grid - Inverts from light gray lines to dark gray lines */}
      <div className="absolute top-0 left-0 w-full h-full bg-[linear-gradient(rgba(0,0,0,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(0,0,0,0.05)_1px,transparent_1px)] dark:bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:50px_50px] pointer-events-none opacity-50 dark:opacity-30 transition-colors"></div>

      <div className="z-10 w-full max-w-2xl px-6 flex flex-col items-center">
        
        {/* System Status */}
        <div className="mb-12 flex flex-col items-center">
          <Terminal size={48} className="text-black dark:text-white mb-6 transition-colors" strokeWidth={1} />
          <div className="flex items-center gap-3 border border-gray-300 dark:border-[#444] bg-gray-50 dark:bg-[#050505] px-4 py-2 transition-colors">
            {/* The Pulse Dot - Inverts its glow shadow */}
            <div className="w-2 h-2 bg-black dark:bg-white rounded-full animate-pulse shadow-[0_0_8px_rgba(0,0,0,0.5)] dark:shadow-[0_0_8px_rgba(255,255,255,1)] transition-colors"></div>
            <span className="text-[10px] text-black dark:text-white tracking-widest uppercase font-bold transition-colors">System Status: Online</span>
            <span className="text-[10px] text-gray-500 dark:text-gray-200 border-l border-gray-300 dark:border-[#444] pl-3 ml-1 transition-colors">V_4.0.1</span>
          </div>
        </div>

        {/* Title Block */}
        <div className="text-center space-y-6 mb-16 w-full">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tighter uppercase text-black dark:text-white drop-shadow-sm dark:drop-shadow-md transition-colors">
            Agentic_Project<br/>Mentor
          </h1>
          
          <div className="border-l-2 border-black dark:border-white pl-4 max-w-lg mx-auto text-left space-y-2 transition-colors">
            <p className="text-gray-700 dark:text-gray-200 text-sm flex gap-2 transition-colors">
              <span className="text-black dark:text-white font-bold transition-colors">&gt;_</span>
              Transform unstructured ideas into architect-level system designs.
            </p>
            <p className="text-gray-700 dark:text-gray-200 text-sm flex gap-2 transition-colors">
              <span className="text-black dark:text-white font-bold transition-colors">&gt;_</span>
              Multi-agent orchestration protocol ready for execution.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
          
          {/* Button 1: Authenticate */}
          <Link
            href="/login"
            className="flex-1 sm:max-w-[220px] border border-gray-300 dark:border-[#555] bg-gray-50 dark:bg-[#050505] hover:border-black dark:hover:border-white transition-all p-4 flex flex-col items-start group relative"
          >
            {/* Corner Accents - Invert color on theme swap */}
            <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-black dark:border-white opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-black dark:border-white opacity-0 group-hover:opacity-100 transition-opacity"></div>
            
            <ShieldAlert size={14} className="text-gray-500 dark:text-gray-200 mb-3 group-hover:text-black dark:group-hover:text-white transition-colors" />
            <span className="text-[10px] text-gray-500 dark:text-gray-200 tracking-widest uppercase mb-1 font-bold transition-colors">Req_Access</span>
            <span className="text-sm font-bold text-black dark:text-white uppercase tracking-widest transition-colors">Authenticate</span>
          </Link>

          {/* Button 2: Dashboard Bypass */}
          <Link
            href="/dashboard"
            className="flex-1 sm:max-w-[220px] border border-black dark:border-white bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200 transition-all p-4 flex flex-col items-start group"
          >
            <ChevronRight size={14} className="text-white dark:text-black mb-3 group-hover:translate-x-1 transition-transform" />
            <span className="text-[10px] text-gray-400 dark:text-gray-700 tracking-widest uppercase mb-1 font-bold transition-colors">System_Bypass</span>
            <span className="text-sm font-bold uppercase tracking-widest text-white dark:text-black transition-colors">Init_Dashboard</span>
          </Link>

        </div>
      </div>

      {/* Background Terminal Logs */}
      <div className="absolute bottom-4 left-4 text-[10px] text-gray-400 dark:text-gray-200 space-y-1 opacity-80 hidden sm:block font-bold transition-colors">
        <p>14:02:11 -- INIT SEQUENCE STARTED</p>
        <p>14:02:12 -- LOADING ORCHESTRATOR_MODULE</p>
        <p>14:02:12 -- WAITING FOR USER INPUT...</p>
      </div>
    </div>
  );
}