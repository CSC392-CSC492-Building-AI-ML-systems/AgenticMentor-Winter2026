import { Network, Copy } from "lucide-react";

export default function ArchitecturePanel() {
  return (
    <>
      <div className="h-10 border-b border-gray-300 dark:border-[#444] flex items-center justify-between px-4 bg-gray-50 dark:bg-black flex-shrink-0 transition-colors">
        <div className="flex items-center gap-2 text-black dark:text-white">
          <Network size={12} />
          <span className="text-[10px] tracking-widest uppercase font-bold text-black dark:text-white">Architecture_Graph</span>
        </div>
        <div className="flex gap-2">
          <button className="text-[10px] font-bold border border-gray-300 dark:border-[#555] px-2 py-1 text-gray-600 dark:text-gray-300 hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors flex items-center gap-1 bg-white dark:bg-transparent">
            <Copy size={10} /> COPY_MERMAID
          </button>
          <button className="text-[10px] font-bold border border-black dark:border-[#555] px-2 py-1 text-white dark:text-white bg-black dark:bg-transparent hover:bg-gray-800 dark:hover:bg-white dark:hover:text-black transition-colors">
            REFRESH_VIEW
          </button>
        </div>
      </div>

      <div className="flex-1 p-4 md:p-8 flex flex-col justify-start sm:justify-center items-center relative overflow-auto bg-gray-100 dark:bg-[#0a0a0a] transition-colors">
        <div className="border border-gray-300 dark:border-[#555] p-8 md:p-12 w-full max-w-lg min-w-[450px] relative bg-white dark:bg-[#030303] shadow-lg dark:shadow-2xl my-auto transition-colors">
          <div className="flex justify-between items-center mb-12">
            <div className="px-4 py-2 bg-black dark:bg-white text-white dark:text-black text-xs font-bold border border-black dark:border-white transition-colors">
              Client_App
            </div>
            <div className="flex-1 flex flex-col items-center justify-center relative px-4 text-black dark:text-white transition-colors">
              <span className="text-[10px] absolute -top-4 font-bold">POST</span>
              <span className="text-[10px] absolute -bottom-4 font-bold">/v1/auth</span>
              <div className="w-full h-[1px] bg-black dark:bg-white relative transition-colors">
                <div className="absolute right-0 -top-1 border-t-[5px] border-t-transparent border-l-[5px] border-l-black dark:border-l-white border-b-[5px] border-b-transparent transition-colors"></div>
              </div>
            </div>
            <div className="px-4 py-2 border border-black dark:border-white text-black dark:text-white text-xs font-bold transition-colors">
              Auth_Gateway
            </div>
          </div>

          <div className="flex justify-between items-center mb-8 opacity-80">
            <div className="px-4 py-2 border border-gray-400 dark:border-[#888] text-gray-700 dark:text-gray-200 text-xs font-bold bg-gray-50 dark:bg-black transition-colors">
              Redis_Cache
            </div>
            <div className="flex-1 flex flex-col items-center justify-center relative px-4 text-gray-600 dark:text-gray-200 transition-colors">
              <span className="text-[10px] absolute -top-4 font-bold">Lookup_Token</span>
              <div className="w-full h-[1px] bg-gray-400 dark:bg-[#888] relative transition-colors">
                 <div className="absolute left-0 -top-1 border-t-[5px] border-t-transparent border-r-[5px] border-r-gray-400 dark:border-r-[#888] border-b-[5px] border-b-transparent transition-colors"></div>
              </div>
            </div>
            <div className="px-4 py-2 border border-gray-400 dark:border-[#888] text-gray-700 dark:text-gray-200 text-xs font-bold bg-gray-50 dark:bg-black transition-colors">
              Auth_Gateway
            </div>
          </div>

          <div className="text-center mt-12">
             <span className="text-[10px] font-bold border border-dashed border-gray-400 dark:border-[#888] text-gray-600 dark:text-gray-200 px-4 py-1 bg-gray-50 dark:bg-black transition-colors">
               LAYER_SECURE_TRANSPORT_ENABLED
             </span>
          </div>
        </div>
      </div>

      <div className="h-32 border-t border-gray-300 dark:border-[#444] bg-gray-50 dark:bg-[#050505] p-4 text-[11px] text-gray-700 dark:text-gray-200 overflow-y-auto flex-shrink-0 transition-colors">
        <div className="flex gap-4"><span className="text-black dark:text-white font-bold">01</span><span className="text-black dark:text-white font-bold">sequenceDiagram</span></div>
        <div className="flex gap-4"><span className="text-black dark:text-white font-bold">02</span><span>  Client_App-&gt;&gt;Auth_Gateway: Secure Handshake</span></div>
        <div className="flex gap-4"><span className="text-black dark:text-white font-bold">03</span><span>  Auth_Gateway-&gt;&gt;Identity_Provider: Validate Payload</span></div>
      </div>
    </>
  );
}