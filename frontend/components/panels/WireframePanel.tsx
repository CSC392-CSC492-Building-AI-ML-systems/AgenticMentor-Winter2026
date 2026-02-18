import { LayoutTemplate, Plus } from "lucide-react";

export default function WireframePanel() {
  return (
    <>
      <div className="h-10 border-b border-[#444] flex items-center justify-between px-4 bg-black">
        <div className="flex items-center gap-2 text-white">
          <LayoutTemplate size={12} />
          <span className="text-[10px] tracking-widest uppercase font-bold text-white">UI_Wireframe</span>
        </div>
        <span className="text-[10px] text-gray-200 font-bold">L-FID_01</span>
      </div>

      <div className="flex-1 p-6 overflow-y-auto relative">
        <div className="border border-[#555] p-4 mb-8 bg-[#050505]">
          <div className="border border-[#555] aspect-video flex flex-col p-4 bg-black">
             <div className="flex justify-between items-center mb-8">
                <div className="w-16 h-2 bg-[#555]"></div>
                <div className="flex gap-2">
                   <div className="w-2 h-2 rounded-full border border-gray-200"></div>
                   <div className="w-2 h-2 rounded-full bg-white"></div>
                </div>
             </div>
             <div className="m-auto border border-white w-2/3 h-2/3 p-4 flex flex-col">
                <div className="w-8 h-1 bg-white mb-6"></div>
                <div className="w-full h-4 border border-[#555] mb-3"></div>
                <div className="w-full h-4 border border-[#555] mb-auto"></div>
                <div className="w-12 h-4 bg-white self-end"></div>
             </div>
          </div>
        </div>

        <div className="flex justify-between items-center mb-4">
          <h2 className="text-[10px] font-bold text-white tracking-widest uppercase">Assets_Inventory</h2>
          <span className="text-[10px] text-gray-200 font-bold">04_UNITS</span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="border border-[#555] p-4 flex flex-col items-center justify-center gap-2 aspect-square bg-[#050505]">
            <div className="w-full h-full border border-dashed border-[#888]"></div>
            <span className="text-[8px] text-gray-200 font-bold tracking-widest">THUMB_PLACEHOLDER</span>
          </div>
          <div className="border border-[#555] p-4 flex flex-col justify-end gap-2 aspect-square bg-[#050505]">
            <div className="w-full h-6 bg-white mb-auto"></div>
            <div className="w-full h-4 border border-[#555]"></div>
            <span className="text-[8px] text-gray-200 font-bold tracking-widest pt-2">BTN_GROUP_V2</span>
          </div>
        </div>
      </div>

      {/* <div className="absolute bottom-6 right-6 w-72 border border-[#555] bg-black shadow-2xl">
        <div className="h-8 border-b border-[#555] flex items-center justify-between px-3 bg-[#050505]">
           <span className="text-[9px] font-bold tracking-widest uppercase text-white">Terminal_Output</span>
           <div className="w-2 h-2 bg-white"></div>
        </div>
        <div className="p-3 text-[10px] text-gray-200 space-y-2 font-mono font-bold">
           <p><span className="text-white">14:02:11</span> Syncing context...</p>
           <p><span className="text-white">14:02:12</span> Rendering UI layer</p>
           <p><span className="text-white">14:02:12</span> <span className="text-white bg-[#222] px-1">[OK] Build success</span></p>
           <div className="w-full h-[1px] bg-[#555] mt-2"></div>
        </div>
      </div> */}
    </>
  );
}