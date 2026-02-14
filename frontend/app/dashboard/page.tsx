import TopNav from "@/components/layout/TopNav";
import ProjectNode from "@/components/dashboard/ProjectNode";
import Link from "next/link";
import { Terminal, Plus, Search } from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="flex flex-col h-screen w-full bg-black overflow-hidden font-mono selection:bg-gray-700 selection:text-white">
      {/* Global Command Top Nav */}
      <TopNav />

      <main className="flex-1 flex flex-col overflow-hidden">
        
        {/* Terminal-Style Header / Search Bar */}
        <header className="px-8 py-6 border-b border-[#333] bg-[#050505] flex items-center justify-between flex-shrink-0">
          <div>
            <h1 className="text-xl font-bold text-white tracking-widest uppercase flex items-center gap-3">
              <Terminal size={20} className="text-gray-400" />
              SYSTEM_INDEX
            </h1>
            <p className="text-[10px] text-gray-500 tracking-widest uppercase mt-2">
              Directory of active operational workspaces
            </p>
          </div>
          
          <div className="flex items-center gap-6">
            {/* Command-line style search */}
            <div className="flex items-center border border-[#444] bg-black focus-within:border-white transition-colors h-10 w-80">
              <div className="px-3 flex items-center justify-center text-gray-500 border-r border-[#444]">
                <Search size={14} />
              </div>
              <span className="pl-3 text-white text-xs font-bold">&gt;_</span>
              <input 
                type="text" 
                placeholder="grep -i 'node_name'" 
                className="flex-1 bg-transparent border-none text-xs text-white placeholder:text-[#555] px-2 py-2 focus:outline-none"
              />
            </div>
            
            {/* Initialize Button */}
            <button className="flex items-center gap-2 h-10 px-6 bg-white text-black text-[10px] font-bold tracking-widest uppercase hover:bg-gray-200 transition-colors">
              <Plus size={14} strokeWidth={3} />
              INITIALIZE_NODE
            </button>
          </div>
        </header>

        {/* System Nodes Grid */}
        <div className="flex-1 overflow-y-auto p-8 bg-black">
          
          <div className="flex items-center justify-between mb-8 border-b border-[#333] pb-2">
            <h2 className="text-[10px] font-bold text-gray-400 tracking-widest uppercase">
              ACTIVE_WORKSPACE_NODES <span className="text-gray-600 ml-2">[04_TOTAL]</span>
            </h2>
            <div className="text-[10px] text-gray-500 tracking-widest uppercase flex gap-4">
              <button className="text-white">SORT: RECENT</button>
              <button className="hover:text-gray-300">SORT: STATUS</button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
            <Link href="/project/1" className="block outline-none">
              <ProjectNode 
                id="PRJ-CRM-01"
                name="CRM System Architecture"
                description="Internal customer relationship management system. Focus on modular API design and RBAC implementation."
                status="ONLINE"
                lastSync="14:02:11"
                techStack={["Next.js", "Python", "Redis"]}
              />
            </Link>
            
            <Link href="/project/2" className="block outline-none">
              <ProjectNode 
                id="PRJ-MKT-02"
                name="Marketing Engine V2"
                description="High-throughput landing page generation system with integrated A/B testing matrix."
                status="ONLINE"
                lastSync="09:14:55"
                techStack={["React", "Node.js", "PostgreSQL"]}
              />
            </Link>

            <Link href="/project/3" className="block outline-none">
              <ProjectNode 
                id="PRJ-API-03"
                name="Mobile Gateway API"
                description="Backend secure transport layer for the iOS/Android mobile client fleet."
                status="BUILDING"
                lastSync="YESTERDAY"
                techStack={["Golang", "gRPC", "Docker"]}
              />
            </Link>

            <Link href="/project/4" className="block outline-none opacity-50 hover:opacity-100 transition-opacity">
              <ProjectNode 
                id="PRJ-LGC-04"
                name="Legacy Mainframe Auth"
                description="Deprecation mapping and token translation layer for the old V1 monolith."
                status="IDLE"
                lastSync="1 WEEK AGO"
                techStack={["Java", "SOAP"]}
              />
            </Link>
          </div>

        </div>
      </main>
    </div>
  );
}