import { LayoutTemplate, Plus } from "lucide-react";

export default function WireframePanel() {
  return (
    <>
      <div className="h-10 border-b border-[#333] flex items-center justify-between px-4 bg-black">
        <div className="flex items-center gap-2 text-gray-400">
          <LayoutTemplate size={12} />
          <span className="text-[10px] tracking-widest uppercase font-bold">UI_Wireframe</span>
        </div>
        <span className="text-[10px] text-gray-500">L-FID_01</span>
      </div>

      <div className="flex-1 p-6 overflow-y-auto relative">
        {/* Main Wireframe Box */}
        <div className="border border-[#333] p-4 mb-8">
          <div className="border border-[#333] aspect-video flex flex-col p-4 bg-[#050505]">
             {/* Header mock */}
             <div className="flex justify-between items-center mb-8">
                <div className="w-16 h-2 bg-[#333]"></div>
                <div className="flex gap-2">
                   <div className="w-2 h-2 rounded-full border border-[#555]"></div>
                   <div className="w-2 h-2 rounded-full bg-white"></div>
                </div>
             </div>
             {/* Modal mock */}
             <div className="m-auto border border-white w-2/3 h-2/3 p-4 flex flex-col">
                <div className="w-8 h-1 bg-white mb-6"></div>
                <div className="w-full h-4 border border-[#333] mb-3"></div>
                <div className="w-full h-4 border border-[#333] mb-auto"></div>
                <div className="w-12 h-4 bg-white self-end"></div>
             </div>
          </div>
        </div>

        {/* Assets Inventory */}
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-[10px] font-bold text-gray-400 tracking-widest uppercase">Assets_Inventory</h2>
          <span className="text-[10px] text-gray-600">04_UNITS</span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="border border-[#333] p-4 flex flex-col items-center justify-center gap-2 aspect-square">
            <div className="w-full h-full border border-dashed border-[#444]"></div>
            <span className="text-[8px] text-[#666] tracking-widest">THUMB_PLACEHOLDER</span>
          </div>
          <div className="border border-[#333] p-4 flex flex-col justify-end gap-2 aspect-square">
            <div className="w-full h-6 bg-white mb-auto"></div>
            <div className="w-full h-4 border border-[#333]"></div>
            <span className="text-[8px] text-[#666] tracking-widest pt-2">BTN_GROUP_V2</span>
          </div>
        </div>
      </div>

      {/* Floating Terminal Output */}
      <div className="absolute bottom-6 right-6 w-72 border border-[#333] bg-black shadow-2xl">
        <div className="h-8 border-b border-[#333] flex items-center justify-between px-3">
           <span className="text-[9px] font-bold tracking-widest uppercase text-white">Terminal_Output</span>
           <div className="w-2 h-2 bg-[#333]"></div>
        </div>
        <div className="p-3 text-[10px] text-gray-400 space-y-2 font-mono">
           <p><span className="text-[#666]">14:02:11</span> Syncing context...</p>
           <p><span className="text-[#666]">14:02:12</span> Rendering UI layer</p>
           <p><span className="text-[#666]">14:02:12</span> <span className="text-white">[OK] Build success</span></p>
           <div className="w-full h-[1px] bg-white mt-2"></div>
        </div>
      </div>

      {/* Floating Plus Button */}
      <button className="absolute bottom-6 right-6 translate-y-12 translate-x-12 w-8 h-8 border border-[#333] flex items-center justify-center hover:bg-[#111] transition-colors text-white z-10 hidden">
         <Plus size={16} />
      </button>
    </>
  );
}