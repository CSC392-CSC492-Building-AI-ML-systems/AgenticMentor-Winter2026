import TopNav from "@/components/layout/TopNav";
import ProjectNode from "@/components/dashboard/ProjectNode";
import Link from "next/link";
import { Terminal, Plus, Search } from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="flex flex-col h-screen w-full bg-white dark:bg-black overflow-hidden font-mono selection:bg-gray-300 dark:selection:bg-gray-200 selection:text-black transition-colors">
      <TopNav />

      <main className="flex-1 flex flex-col overflow-hidden">
        
        {/* HEADER SECTION */}
        <header className="px-8 py-6 border-b border-gray-300 dark:border-[#444] bg-gray-50 dark:bg-[#050505] flex flex-col md:flex-row md:items-center justify-between flex-shrink-0 gap-4 transition-colors">
          <div>
            <h1 className="text-xl font-bold text-black dark:text-white tracking-widest uppercase flex items-center gap-3 transition-colors">
              <Terminal size={20} className="text-black dark:text-white transition-colors" />
              SYSTEM_INDEX
            </h1>
            <p className="text-[10px] text-gray-600 dark:text-gray-200 tracking-widest uppercase mt-2 font-bold transition-colors">
              Directory of active operational workspaces
            </p>
          </div>
          
          <div className="flex items-center gap-4 sm:gap-6">
            
            {/* Search Bar */}
            <div className="hidden sm:flex items-center border border-gray-300 dark:border-[#555] bg-white dark:bg-black focus-within:border-black dark:focus-within:border-white transition-colors h-10 w-64 md:w-80">
              <div className="px-3 flex items-center justify-center text-black dark:text-white border-r border-gray-300 dark:border-[#555] transition-colors">
                <Search size={14} />
              </div>
              <span className="pl-3 text-black dark:text-white text-xs font-bold transition-colors">&gt;_</span>
              <input 
                type="text" 
                placeholder="grep -i 'node_name'" 
                className="flex-1 bg-transparent border-none text-xs text-black dark:text-white placeholder:text-gray-500 dark:placeholder:text-gray-400 px-2 py-2 focus:outline-none font-bold"
              />
            </div>
            
            {/* Action Button */}
            <button className="flex items-center gap-2 h-10 px-6 bg-black dark:bg-white text-white dark:text-black text-[10px] font-bold tracking-widest uppercase hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors">
              <Plus size={14} strokeWidth={3} />
              INITIALIZE_NODE
            </button>
          </div>
        </header>

        {/* MAIN CONTENT / GRID SECTION */}
        <div className="flex-1 overflow-y-auto p-8 bg-white dark:bg-black transition-colors">
          
          {/* Section Toolbar */}
          <div className="flex items-center justify-between mb-8 border-b border-gray-300 dark:border-[#444] pb-2 transition-colors">
            <h2 className="text-[10px] font-bold text-black dark:text-white tracking-widest uppercase transition-colors">
              ACTIVE_WORKSPACE_NODES <span className="text-gray-500 dark:text-gray-200 ml-2 transition-colors">[{`04_TOTAL`}]</span>
            </h2>
            <div className="text-[10px] tracking-widest uppercase flex gap-4 font-bold">
              <button className="text-black dark:text-white underline underline-offset-4 transition-colors">SORT: RECENT</button>
              <button className="text-gray-500 dark:text-gray-400 hover:text-black dark:hover:text-white transition-colors">SORT: STATUS</button>
            </div>
          </div>

          {/* Project Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
            <Link href="/project/1" className="block outline-none">
              <ProjectNode id="PRJ-CRM-01" name="CRM System Architecture" description="Internal CRM system. Focus on modular API design and RBAC implementation." status="ONLINE" lastSync="14:02:11" techStack={["Next.js", "Python", "Redis"]} />
            </Link>
            <Link href="/project/2" className="block outline-none">
              <ProjectNode id="PRJ-MKT-02" name="Marketing Engine V2" description="High-throughput landing page generation system with A/B testing matrix." status="ONLINE" lastSync="09:14:55" techStack={["React", "Node.js", "PostgreSQL"]} />
            </Link>
            <Link href="/project/3" className="block outline-none">
              <ProjectNode id="PRJ-API-03" name="Mobile Gateway API" description="Backend secure transport layer for the iOS/Android mobile client fleet." status="BUILDING" lastSync="YESTERDAY" techStack={["Golang", "gRPC", "Docker"]} />
            </Link>
            <Link href="/project/4" className="block outline-none opacity-60 hover:opacity-100 transition-opacity">
              <ProjectNode id="PRJ-LGC-04" name="Legacy Mainframe Auth" description="Deprecation mapping and token translation layer for the old V1 monolith." status="IDLE" lastSync="1 WEEK AGO" techStack={["Java", "SOAP"]} />
            </Link>
          </div>

        </div>
      </main>
    </div>
  );
}