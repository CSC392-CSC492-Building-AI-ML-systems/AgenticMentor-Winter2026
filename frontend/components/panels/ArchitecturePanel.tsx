import { Network } from "lucide-react";

export default function ArchitecturePanel() {
  return (
    <>
      <div className="h-10 border-b border-[#333] flex items-center justify-between px-4 bg-black">
        <div className="flex items-center gap-2 text-gray-300">
          <Network size={12} />
          <span className="text-[10px] tracking-widest uppercase font-bold text-white">Architecture_Graph</span>
        </div>
        <button className="text-[10px] border border-[#555] px-2 py-1 text-gray-300 hover:text-white hover:border-white transition-colors">
          REFRESH_VIEW
        </button>
      </div>

      <div className="flex-1 p-8 flex flex-col justify-center items-center relative">
        <div className="border border-[#444] p-12 w-full max-w-lg relative">
          
          <div className="flex justify-between items-center mb-12">
            <div className="px-4 py-2 bg-white text-black text-xs font-bold border border-white">
              Client_App
            </div>
            <div className="flex-1 flex flex-col items-center justify-center relative px-4 text-gray-300">
              <span className="text-[10px] absolute -top-4 font-bold text-white">POST</span>
              <span className="text-[10px] absolute -bottom-4">/v1/auth</span>
              <div className="w-full h-[1px] bg-white relative">
                <div className="absolute right-0 -top-1 border-t-[5px] border-t-transparent border-l-[5px] border-l-white border-b-[5px] border-b-transparent"></div>
              </div>
            </div>
            <div className="px-4 py-2 border border-white text-white text-xs font-bold">
              Auth_Gateway
            </div>
          </div>

          <div className="flex justify-between items-center mb-8 opacity-60">
            <div className="px-4 py-2 border border-gray-400 text-gray-200 text-xs font-bold">
              Redis_Cache
            </div>
            <div className="flex-1 flex flex-col items-center justify-center relative px-4 text-gray-300">
              <span className="text-[10px] absolute -top-4">Lookup_Token</span>
              <div className="w-full h-[1px] bg-gray-400 relative">
                 <div className="absolute left-0 -top-1 border-t-[5px] border-t-transparent border-r-[5px] border-r-gray-400 border-b-[5px] border-b-transparent"></div>
              </div>
            </div>
            <div className="px-4 py-2 border border-gray-400 text-gray-200 text-xs font-bold">
              Auth_Gateway
            </div>
          </div>

          <div className="text-center mt-12">
             <span className="text-[10px] border border-dashed border-gray-500 text-gray-300 px-4 py-1">LAYER_SECURE_TRANSPORT_ENABLED</span>
          </div>
        </div>
      </div>

      <div className="h-32 border-t border-[#333] bg-[#050505] p-4 text-[11px] text-gray-300 overflow-y-auto">
        <div className="flex gap-4"><span className="text-gray-500">01</span><span className="text-white font-bold">sequenceDiagram</span></div>
        <div className="flex gap-4"><span className="text-gray-500">02</span><span>  Client_App-&gt;&gt;Auth_Gateway: Secure Handshake</span></div>
        <div className="flex gap-4"><span className="text-gray-500">03</span><span>  Auth_Gateway-&gt;&gt;Identity_Provider: Validate Payload</span></div>
      </div>
    </>
  );
}