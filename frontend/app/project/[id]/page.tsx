import TopNav from "@/components/layout/TopNav";
import RequirementPanel from "@/components/panels/RequirementPanel";
import ArchitecturePanel from "@/components/panels/ArchitecturePanel";
import WireframePanel from "@/components/panels/WireframePanel";
import CommandInput from "@/components/command/CommandInput";

export default function ProjectPage() {
  return (
    <div className="flex flex-col h-screen w-full bg-black font-mono selection:bg-gray-200 selection:text-black">
      <TopNav />
      <div className="flex-1 flex overflow-hidden">
        <div className="w-1/4 min-w-[300px] border-r border-[#444] flex flex-col h-full relative">
          <RequirementPanel />
        </div>
        <div className="w-[45%] border-r border-[#444] flex flex-col h-full">
          <ArchitecturePanel />
        </div>
        <div className="w-[30%] min-w-[350px] flex flex-col h-full relative">
          <WireframePanel />
        </div>
      </div>
      <CommandInput />
    </div>
  );
}