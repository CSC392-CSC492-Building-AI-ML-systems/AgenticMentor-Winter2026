import { MoreHorizontal, Folder, Clock, ArrowRight } from "lucide-react";
import Link from "next/link";

interface ProjectCardProps {
  title: string;
  description: string;
  lastEdited: string;
  status: "Active" | "Archived" | "Completed";
  color: string; // e.g., "bg-blue-600"
}

export default function ProjectCard({ title, description, lastEdited, status, color }: ProjectCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow cursor-pointer group flex flex-col h-full">
      <div className="flex justify-between items-start mb-4">
        <div className={`w-10 h-10 ${color} rounded-lg flex items-center justify-center text-white`}>
          <Folder size={20} fill="currentColor" fillOpacity={0.2} />
        </div>
        <button className="text-gray-400 hover:text-gray-600">
          <MoreHorizontal size={20} />
        </button>
      </div>

      <h3 className="font-bold text-gray-900 text-lg mb-1 group-hover:text-blue-600 transition-colors">
        {title}
      </h3>
      <p className="text-sm text-gray-500 mb-6 flex-1">
        {description}
      </p>

      <div className="flex items-center justify-between pt-4 border-t border-gray-50 mt-auto">
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <Clock size={14} />
          <span>{lastEdited}</span>
        </div>
        
        <span className={`px-2 py-1 rounded-full text-[10px] font-medium uppercase tracking-wide
          ${status === "Active" ? "bg-emerald-50 text-emerald-600 border border-emerald-100" : 
            status === "Completed" ? "bg-blue-50 text-blue-600 border border-blue-100" :
            "bg-gray-100 text-gray-500 border border-gray-200"
          }`}>
          {status}
        </span>
      </div>
    </div>
  );
}