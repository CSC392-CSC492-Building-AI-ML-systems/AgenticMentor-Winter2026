"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import TopNav from "@/components/layout/TopNav";
import ConsoleWindow from "@/components/console/ConsoleWindow";
import RequirementPanel from "@/components/panels/RequirementPanel";
import ArchitecturePanel from "@/components/panels/ArchitecturePanel";
import WireframePanel from "@/components/panels/WireframePanel";
import ExecutionPanel from "@/components/panels/ExecutionPanel";
import RequireAuth from "@/components/auth/RequireAuth";
import { FileDown } from "lucide-react";
import { useProjectStore } from "@/store/useProjectStore";
import { useAuthStore } from "@/store/useAuthStore";
import { fetchWithAuth } from "@/lib/api";

export default function ProjectPage() {
  const [consoleOpen, setConsoleOpen] = useState(true);
  const params = useParams();
  const projectId = params?.id as string | undefined;

  const { setProjectId, resetProject, applyStateSnapshot, setAvailableAgents, setIsLoading, exportArtifacts, activeTab, setActiveTab } = useProjectStore();
  const { idToken } = useAuthStore();

  useEffect(() => {
    if (!projectId || !idToken) return;
    resetProject();
    setProjectId(projectId);

    const loadProject = async () => {
      setIsLoading(true);
      try {
        const res = await fetchWithAuth(`/projects/${projectId}`, { token: idToken });
        if (res.ok) {
          const data = await res.json();
          applyStateSnapshot(data);
          if (data.available_agents) setAvailableAgents(data.available_agents);
        }
      } catch (err) {
        console.error("[ProjectPage] Failed to load project state:", err);
      } finally {
        setIsLoading(false);
      }
    };

    loadProject();
  }, [projectId, idToken]);

  const handleDownload = () => {
    if (!exportArtifacts?.markdown_content) return;
    const blob = new Blob([exportArtifacts.markdown_content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "project_spec.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  const tabs = [
    { id: "req", label: "01_Requirements" },
    { id: "arch", label: "02_Architecture" },
    { id: "exec", label: "03_Execution_Plan" },
    { id: "mock", label: "04_Mockups" }
  ];

  return (
    <RequireAuth>
    <div className="flex flex-col h-screen w-full bg-white dark:bg-black font-mono selection:bg-gray-300 dark:selection:bg-gray-200 selection:text-black transition-colors">
      <TopNav />
      
      {/* Scrollable Tab Bar */}
      <div className="flex overflow-x-auto border-b border-gray-300 dark:border-[#444] bg-gray-50 dark:bg-[#050505] flex-shrink-0 [&::-webkit-scrollbar]:hidden transition-colors">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-6 py-3 text-[10px] font-bold tracking-widest uppercase whitespace-nowrap border-r border-gray-300 dark:border-[#444] transition-colors
              ${activeTab === tab.id 
                ? "bg-white dark:bg-black text-black dark:text-white border-b-2 border-b-black dark:border-b-white" 
                : "text-gray-500 hover:bg-gray-200 dark:hover:bg-[#111] hover:text-black dark:hover:text-gray-300 border-b-2 border-b-transparent"
              }
            `}
          >
            {tab.label}
          </button>
        ))}
        <div className="flex-1 border-b-2 border-b-transparent"></div>
        {exportArtifacts?.markdown_content && (
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-4 py-3 text-[10px] font-bold tracking-widest uppercase whitespace-nowrap border-l border-green-600 bg-green-600 text-white hover:bg-green-700 transition-colors flex-shrink-0"
          >
            <FileDown size={12} />
            Export_Spec
          </button>
        )}
      </div>
      
      {/* Active Panel + Right Console */}
      <div className="flex-1 flex overflow-hidden bg-white dark:bg-black transition-colors relative">
        {/* Panel Content */}
        <div className="flex-1 flex flex-col h-full overflow-hidden">
          {activeTab === "req" && <RequirementPanel />}
          {activeTab === "arch" && <ArchitecturePanel />}
          {activeTab === "exec" && <ExecutionPanel />}
          {activeTab === "mock" && <WireframePanel />}
        </div>

        {/* Toggle Button */}
        <button
          onClick={() => setConsoleOpen((v) => !v)}
          className="absolute top-1/2 -translate-y-1/2 z-50 bg-white dark:bg-black border border-gray-300 dark:border-[#444] text-black dark:text-white text-[10px] font-bold uppercase tracking-widest px-1 py-3 hover:bg-gray-100 dark:hover:bg-[#111] transition-all"
          style={{ right: consoleOpen ? "380px" : "0px" }}
          title={consoleOpen ? "Close console" : "Open console"}
        >
          {consoleOpen ? "›" : "‹"}
        </button>

        {/* Right Console Sidebar — always mounted to preserve state */}
        <div className={`flex-shrink-0 border-l border-gray-300 dark:border-[#444] flex flex-col h-full transition-all duration-200 ${consoleOpen ? "w-[380px]" : "w-0 overflow-hidden border-l-0"}`}>
          <ConsoleWindow />
        </div>
      </div>
    </div>
    </RequireAuth>
  );
}