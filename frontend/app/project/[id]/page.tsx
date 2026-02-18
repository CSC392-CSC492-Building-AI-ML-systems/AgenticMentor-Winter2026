"use client";
import { useState } from "react";
import TopNav from "@/components/layout/TopNav";
import ConsoleWindow from "@/components/console/ConsoleWindow";
import RequirementPanel from "@/components/panels/RequirementPanel";
import ArchitecturePanel from "@/components/panels/ArchitecturePanel";
import WireframePanel from "@/components/panels/WireframePanel";
import ExecutionPanel from "@/components/panels/ExecutionPanel";
import { ChevronLeft, ChevronRight } from "lucide-react";

export default function ProjectPage() {
  const [panels, setPanels] = useState({
    req: true,
    arch: true,
    exec: true,
    mock: true,
  });

  const togglePanel = (key: keyof typeof panels) => {
    setPanels(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const PanelWrapper = ({ id, title, isExpanded, children }: { id: keyof typeof panels, title: string, isExpanded: boolean, children: React.ReactNode }) => {
    if (!isExpanded) {
      // COLLAPSED STATE: Thin vertical strip
      return (
        <div 
          onClick={() => togglePanel(id)} 
          className="w-10 border-r border-[#444] flex flex-col items-center py-4 bg-[#050505] hover:bg-white hover:text-black transition-colors cursor-pointer flex-shrink-0 text-gray-500 group"
          title={`Expand ${title}`}
        >
          <ChevronRight size={14} className="mb-6 group-hover:text-black stroke-[3px]" />
          <span className="text-[10px] font-bold tracking-widest uppercase rotate-180 group-hover:text-black whitespace-nowrap" style={{ writingMode: 'vertical-rl' }}>
            {title}
          </span>
        </div>
      );
    }

    return (
      // EXPANDED STATE: Full panel with a vertical toggle bar on the right
      <div className="flex-1 min-w-[350px] flex h-full border-r border-[#444] bg-black overflow-hidden transition-all">
        
        {/* The Panel Content */}
        <div className="flex-1 flex flex-col h-full overflow-hidden w-full relative">
           {children}
        </div>

        {/* The Vertical Toggle Bar (Replaces overlapping icons) */}
        <div
           onClick={() => togglePanel(id)}
           className="w-6 bg-[#050505] border-l border-[#444] hover:bg-white hover:text-black text-gray-500 cursor-pointer flex flex-col items-center justify-center transition-colors flex-shrink-0"
           title={`Collapse ${title}`}
        >
           <ChevronLeft size={14} className="stroke-[3px]" />
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-screen w-full bg-black font-mono selection:bg-gray-200 selection:text-black">
      <TopNav />
      
      {/* The Dynamic, Overflow-Safe Flex Grid */}
      <div className="flex-1 flex overflow-hidden">
        <PanelWrapper id="req" title="01_Requirements" isExpanded={panels.req}>
          <RequirementPanel />
        </PanelWrapper>
        
        <PanelWrapper id="arch" title="02_Architecture" isExpanded={panels.arch}>
          <ArchitecturePanel />
        </PanelWrapper>
        
        <PanelWrapper id="exec" title="03_Execution_Plan" isExpanded={panels.exec}>
          <ExecutionPanel />
        </PanelWrapper>

        <PanelWrapper id="mock" title="04_Mockups" isExpanded={panels.mock}>
          <WireframePanel />
        </PanelWrapper>
      </div>

      <ConsoleWindow />
    </div>
  );
}