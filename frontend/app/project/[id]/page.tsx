"use client";
import { useState } from "react";
import TopNav from "@/components/layout/TopNav";
import ConsoleWindow from "@/components/console/ConsoleWindow";
import RequirementPanel from "@/components/panels/RequirementPanel";
import ArchitecturePanel from "@/components/panels/ArchitecturePanel";
import WireframePanel from "@/components/panels/WireframePanel";
import ExecutionPanel from "@/components/panels/ExecutionPanel";

export default function ProjectPage() {
  // 1. State to track the currently active tab
  const [activeTab, setActiveTab] = useState("req");

  // 2. Define our tabs
  const tabs = [
    { id: "req", label: "01_Requirements" },
    { id: "arch", label: "02_Architecture" },
    { id: "exec", label: "03_Execution_Plan" },
    { id: "mock", label: "04_Mockups" }
  ];

  return (
    <div className="flex flex-col h-screen w-full bg-black font-mono selection:bg-gray-200 selection:text-black">
      <TopNav />
      
      {/* 3. Scrollable Tab Bar (Mobile Friendly!) */}
      <div className="flex overflow-x-auto border-b border-[#444] bg-[#050505] flex-shrink-0 [&::-webkit-scrollbar]:hidden">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-6 py-3 text-[10px] font-bold tracking-widest uppercase whitespace-nowrap border-r border-[#444] transition-colors
              ${activeTab === tab.id 
                ? "bg-black text-white border-b-2 border-b-white" // Active State
                : "text-gray-500 hover:bg-[#111] hover:text-gray-300 border-b-2 border-b-transparent" // Inactive State
              }
            `}
          >
            {tab.label}
          </button>
        ))}
        
        {/* Spacer to fill the rest of the bar */}
        <div className="flex-1 border-b-2 border-b-transparent"></div>
      </div>
      
      {/* 4. Active Panel Content Area */}
      <div className="flex-1 flex overflow-hidden bg-black">
        {/* We wrap the active panel in a div that takes up 100% of the width/height */}
        <div className="flex-1 flex flex-col h-full overflow-hidden w-full">
          {activeTab === "req" && <RequirementPanel />}
          {activeTab === "arch" && <ArchitecturePanel />}
          {activeTab === "exec" && <ExecutionPanel />}
          {activeTab === "mock" && <WireframePanel />}
        </div>
      </div>

      {/* 5. Console Window - Still sits nicely at the bottom */}
      <ConsoleWindow />
    </div>
  );
}