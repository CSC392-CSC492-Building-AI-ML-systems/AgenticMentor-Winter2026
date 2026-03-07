import { ExternalLink } from "lucide-react";

export default function MockupView() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm mt-2 w-full max-w-2xl">
      <div className="p-4 flex items-center justify-between border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center text-purple-600 font-bold">
            F
          </div>
          <div>
            <div className="font-semibold text-sm text-gray-900">Login_Flow_UI.fig</div>
            <div className="text-xs text-gray-400">v1.1 • Updated now</div>
          </div>
        </div>
        <button className="text-xs font-medium text-blue-600 flex items-center gap-1 hover:underline">
          Open in Figma <ExternalLink size={12} />
        </button>
      </div>
      
      <div className="flex bg-gray-50">
        {/* Mock Preview Area */}
        <div className="flex-1 p-8 flex justify-center items-center border-r border-gray-200">
          <div className="w-48 bg-white rounded shadow-lg p-4 space-y-3">
             <div className="w-8 h-8 bg-gray-100 rounded-full mx-auto mb-4"></div>
             <div className="h-2 bg-gray-100 rounded w-full"></div>
             <div className="h-2 bg-gray-100 rounded w-3/4"></div>
             <div className="h-8 bg-blue-500 rounded w-full mt-4"></div>
          </div>
        </div>

        {/* Stats Panel */}
        <div className="w-48 p-4 bg-white">
          <div className="mb-4">
             <div className="text-xs font-bold text-gray-400 uppercase mb-2">STATS</div>
             <div className="flex gap-2">
                <span className="px-2 py-1 bg-gray-100 text-xs rounded border border-gray-200">5 Frames</span>
                <span className="px-2 py-1 bg-gray-100 text-xs rounded border border-gray-200">Auto-Layout</span>
             </div>
          </div>
          <div>
             <div className="text-xs font-bold text-gray-400 uppercase mb-2">HISTORY</div>
             <div className="relative pl-3 border-l-2 border-gray-200 space-y-3">
                <div className="relative">
                  <div className="absolute -left-[17px] top-1 w-2.5 h-2.5 bg-blue-500 rounded-full border-2 border-white"></div>
                  <div className="text-xs font-medium text-gray-900">v1.1 - Updates</div>
                  <div className="text-[10px] text-gray-400">Current</div>
                </div>
                <div className="relative opacity-50">
                  <div className="absolute -left-[17px] top-1 w-2.5 h-2.5 bg-gray-300 rounded-full border-2 border-white"></div>
                  <div className="text-xs font-medium text-gray-900">v1.0 - Initial</div>
                  <div className="text-[10px] text-gray-400">10m ago</div>
                </div>
             </div>
          </div>
        </div>
      </div>
    </div>
  )
}