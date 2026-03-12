import { MoreVertical, Download } from "lucide-react";

export default function Topbar() {
  return (
    <div className="h-16 bg-white border-b border-gray-100 flex items-center justify-between px-8 sticky top-0 z-10">
      <h2 className="font-bold text-gray-800">Chat Name</h2>
      <div className="flex items-center gap-4">
        <div className="px-3 py-1 bg-gray-50 rounded-full text-xs text-gray-500">
          Today, 10:23 AM
        </div>
        <button className="p-2 hover:bg-gray-100 rounded-full text-gray-500">
          <Download size={18} />
        </button>
        <button className="p-2 hover:bg-gray-100 rounded-full text-gray-500">
          <MoreVertical size={18} />
        </button>
      </div>
    </div>
  );
}