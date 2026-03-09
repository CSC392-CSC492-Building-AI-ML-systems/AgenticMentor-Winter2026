"use client";
import { useState } from "react";
import TopNav from "@/components/layout/TopNav";
import ConsoleWindow from "@/components/console/ConsoleWindow";
import RequirementPanel from "@/components/panels/RequirementPanel";
import ArchitecturePanel from "@/components/panels/ArchitecturePanel";
import WireframePanel from "@/components/panels/WireframePanel";
import ExecutionPanel from "@/components/panels/ExecutionPanel";
import RequireAuth from "@/components/auth/RequireAuth";

export default function ProjectPage() {
  const [activeTab, setActiveTab] = useState("req");

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
      </div>
      
      {/* Active Panel Content */}
      <div className="flex-1 flex overflow-hidden bg-white dark:bg-black transition-colors">
        <div className="flex-1 flex flex-col h-full overflow-hidden w-full">
          {activeTab === "req" && <RequirementPanel />}
          {activeTab === "arch" && <ArchitecturePanel />}
          {activeTab === "exec" && <ExecutionPanel />}
          {activeTab === "mock" && <WireframePanel />}
        </div>
      </div>

      <ConsoleWindow />
    </div>
    </RequireAuth>
  );
}