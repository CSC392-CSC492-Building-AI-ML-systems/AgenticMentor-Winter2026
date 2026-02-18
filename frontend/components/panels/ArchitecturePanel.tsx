import { Network, Copy } from "lucide-react";

export default function ArchitecturePanel() {
  return (
    <>
      <div className="h-10 border-b border-[#444] flex items-center justify-between px-4 bg-black flex-shrink-0">
        <div className="flex items-center gap-2 text-white">
          <Network size={12} />
          <span className="text-[10px] tracking-widest uppercase font-bold text-white">Architecture_Graph</span>
        </div>
        <div className="flex gap-2">
          {/* Now that the top right is clear, we can safely add a Copy button! */}
          <button className="text-[10px] font-bold border border-[#555] px-2 py-1 text-gray-300 hover:bg-white hover:text-black transition-colors flex items-center gap-1">
            <Copy size={10} /> COPY_MERMAID
          </button>
          <button className="text-[10px] font-bold border border-[#555] px-2 py-1 text-white hover:bg-white hover:text-black transition-colors">
            REFRESH_VIEW
          </button>
        </div>
      </div>

      {/* OVERFLOW FIX: Added overflow-auto here to handle scrolling */}
      <div className="flex-1 p-4 md:p-8 flex flex-col justify-start sm:justify-center items-center relative overflow-auto bg-[#0a0a0a]">
        
        {/* OVERFLOW FIX: Added min-w-[450px] so the graph refuses to crush itself */}
        <div className="border border-[#555] p-8 md:p-12 w-full max-w-lg min-w-[450px] relative bg-[#030303] shadow-2xl my-auto">
          
          <div className="flex justify-between items-center mb-12">
            <div className="px-4 py-2 bg-white text-black text-xs font-bold border border-white">
              Client_App
            </div>
            <div className="flex-1 flex flex-col items-center justify-center relative px-4 text-white">
              <span className="text-[10px] absolute -top-4 font-bold text-white">POST</span>
              <span className="text-[10px] absolute -bottom-4 font-bold">/v1/auth</span>
              <div className="w-full h-[1px] bg-white relative">
                <div className="absolute right-0 -top-1 border-t-[5px] border-t-transparent border-l-[5px] border-l-white border-b-[5px] border-b-transparent"></div>
              </div>
            </div>
            <div className="px-4 py-2 border border-white text-white text-xs font-bold">
              Auth_Gateway
            </div>
          </div>

          <div className="flex justify-between items-center mb-8 opacity-80">
            <div className="px-4 py-2 border border-[#888] text-gray-200 text-xs font-bold bg-black">
              Redis_Cache
            </div>
            <div className="flex-1 flex flex-col items-center justify-center relative px-4 text-gray-200">
              <span className="text-[10px] absolute -top-4 font-bold">Lookup_Token</span>
              <div className="w-full h-[1px] bg-[#888] relative">
                 <div className="absolute left-0 -top-1 border-t-[5px] border-t-transparent border-r-[5px] border-r-[#888] border-b-[5px] border-b-transparent"></div>
              </div>
            </div>
            <div className="px-4 py-2 border border-[#888] text-gray-200 text-xs font-bold bg-black">
              Auth_Gateway
            </div>
          </div>

          <div className="text-center mt-12">
             <span className="text-[10px] font-bold border border-dashed border-[#888] text-gray-200 px-4 py-1 bg-black">
               LAYER_SECURE_TRANSPORT_ENABLED
             </span>
          </div>
        </div>
      </div>

      <div className="h-32 border-t border-[#444] bg-[#050505] p-4 text-[11px] text-gray-200 overflow-y-auto flex-shrink-0">
        <div className="flex gap-4"><span className="text-white font-bold">01</span><span className="text-white font-bold">sequenceDiagram</span></div>
        <div className="flex gap-4"><span className="text-white font-bold">02</span><span>  Client_App-&gt;&gt;Auth_Gateway: Secure Handshake</span></div>
        <div className="flex gap-4"><span className="text-white font-bold">03</span><span>  Auth_Gateway-&gt;&gt;Identity_Provider: Validate Payload</span></div>
      </div>
    </>
  );
}