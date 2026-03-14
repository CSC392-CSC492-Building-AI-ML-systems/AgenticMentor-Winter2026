"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import TopNav from "@/components/layout/TopNav";
import ProjectNode from "@/components/dashboard/ProjectNode";
import { Terminal, Plus, Search } from "lucide-react";
import RequireAuth from "@/components/auth/RequireAuth";
import { useAuthStore } from "@/store/useAuthStore";
import { fetchWithAuth } from "@/lib/api";

interface Project {
  project_id: string;
  project_name: string;
  current_phase: string;
  created_at?: string;
}

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [search, setSearch] = useState("");
  const router = useRouter();
  const { idToken } = useAuthStore();

  useEffect(() => {
    if (!idToken) return;
    fetchWithAuth("/projects", { token: idToken })
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setProjects(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, [idToken]);

  const handleCreateProject = async () => {
    if (!idToken || isCreating) return;
    setIsCreating(true);
    try {
      const res = await fetchWithAuth("/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        token: idToken,
        body: JSON.stringify({ name: `Project_${Date.now()}` }),
      });
      if (res.ok) {
        const data = await res.json();
        const id = data.project_id ?? data.id;
        if (id) router.push(`/project/${id}`);
      }
    } catch (err) {
      console.error("Failed to create project", err);
    } finally {
      setIsCreating(false);
    }
  };

  const filtered = projects.filter((p) =>
    p.project_name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <RequireAuth>
      <div className="flex flex-col h-screen w-full bg-white dark:bg-black overflow-hidden font-mono selection:bg-gray-300 dark:selection:bg-gray-200 selection:text-black transition-colors">
        <TopNav />

        <main className="flex-1 flex flex-col overflow-hidden">
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
              <div className="hidden sm:flex items-center border border-gray-300 dark:border-[#555] bg-white dark:bg-black focus-within:border-black dark:focus-within:border-white transition-colors h-10 w-64 md:w-80">
                <div className="px-3 flex items-center justify-center text-black dark:text-white border-r border-gray-300 dark:border-[#555] transition-colors">
                  <Search size={14} />
                </div>
                <span className="pl-3 text-black dark:text-white text-xs font-bold transition-colors">&gt;_</span>
                <input
                  type="text"
                  placeholder="grep -i 'node_name'"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="flex-1 bg-transparent border-none text-xs text-black dark:text-white placeholder:text-gray-500 dark:placeholder:text-gray-400 px-2 py-2 focus:outline-none font-bold"
                />
              </div>

              <button
                onClick={handleCreateProject}
                disabled={isCreating}
                className="flex items-center gap-2 h-10 px-6 bg-black dark:bg-white text-white dark:text-black text-[10px] font-bold tracking-widest uppercase hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                <Plus size={14} strokeWidth={3} />
                {isCreating ? "INITIALIZING..." : "INITIALIZE_NODE"}
              </button>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto p-8 bg-white dark:bg-black transition-colors">
            <div className="flex items-center justify-between mb-8 border-b border-gray-300 dark:border-[#444] pb-2 transition-colors">
              <h2 className="text-[10px] font-bold text-black dark:text-white tracking-widest uppercase transition-colors">
                ACTIVE_WORKSPACE_NODES{" "}
                <span className="text-gray-500 dark:text-gray-200 ml-2 transition-colors">
                  [{String(filtered.length).padStart(2, "0")}_TOTAL]
                </span>
              </h2>
            </div>

            {filtered.length === 0 && (
              <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">
                -- NO NODES FOUND. PRESS INITIALIZE_NODE TO CREATE ONE --
              </p>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
              {filtered.map((p) => (
                <div
                  key={p.project_id}
                  className="block outline-none cursor-pointer"
                  onClick={() => router.push(`/project/${p.project_id}`)}
                >
                  <ProjectNode
                    id={p.project_id}
                    name={p.project_name}
                    description={`Phase: ${p.current_phase}`}
                    status="ONLINE"
                    lastSync={p.created_at ? new Date(p.created_at).toLocaleTimeString() : "–"}
                    techStack={[]}
                  />
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>
    </RequireAuth>
  );
}
