import TopNav from "@/components/layout/TopNav";
import RequirementPanel from "@/components/panels/RequirementPanel";
import ArchitecturePanel from "@/components/panels/ArchitecturePanel";
import WireframePanel from "@/components/panels/WireframePanel";
import CommandInput from "@/components/command/CommandInput";

export default function ProjectPage() {
  return (
    <div className="flex flex-col h-screen w-full bg-black">
      {/* Top Navigation Bar */}
      <TopNav />

      {/* 3-Column Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column: Requirements (approx 25%) */}
        <div className="w-1/4 min-w-[300px] border-r border-[#333] flex flex-col h-full relative">
          <RequirementPanel />
        </div>

        {/* Center Column: Architecture (approx 45%) */}
        <div className="w-[45%] border-r border-[#333] flex flex-col h-full">
          <ArchitecturePanel />
        </div>

        {/* Right Column: Wireframes & Terminal (approx 30%) */}
        <div className="w-[30%] min-w-[350px] flex flex-col h-full relative">
          <WireframePanel />
        </div>
      </div>

      {/* Bottom Command Bar */}
      <CommandInput />
    </div>
  );
}