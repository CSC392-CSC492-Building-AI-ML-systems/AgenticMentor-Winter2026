"use client";
import { useState } from "react";
import { 
  LayoutDashboard, Folder, MessageSquare, Settings, 
  History, ChevronLeft, ChevronRight 
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div 
      className={cn(
        "h-screen bg-[#F9FAFB] border-r border-gray-200 flex flex-col transition-all duration-300 ease-in-out relative",
        isCollapsed ? "w-[70px]" : "w-[280px]"
      )}
    >
      {/* Collapse Toggle Button */}
      <button 
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-10 w-6 h-6 bg-white border border-gray-200 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 shadow-sm z-50"
      >
        {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      {/* Header */}
      <div className={cn("flex items-center gap-3 px-4 mb-8 mt-6", isCollapsed && "justify-center px-0")}>
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex-shrink-0 flex items-center justify-center text-white font-bold">
          <span className="text-lg">🤖</span>
        </div>
        {!isCollapsed && (
          <div className="overflow-hidden whitespace-nowrap">
            <h1 className="font-bold text-gray-900 leading-none">Agentic Project Mentor</h1>
            <span className="text-[10px] text-gray-500 font-mono">v1.0.0</span>
          </div>
        )}
      </div>

      {/* Navigation Groups */}
      <div className="flex-1 px-3 space-y-8 overflow-y-auto">
        {/* Projects */}
        <div>
          {!isCollapsed && (
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 px-2">Projects</h3>
          )}
          <nav className="space-y-1">
            <NavItem isCollapsed={isCollapsed} icon={<LayoutDashboard size={18} />} label="Main Dashboard" />
            <NavItem isCollapsed={isCollapsed} icon={<Folder size={18} />} label="CRM System" />
          </nav>
        </div>

        {/* Recent Chats - Cleaned up version */}
        <div>
          {!isCollapsed && (
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 px-2">Recent Chats</h3>
          )}
          <nav className="space-y-1">
            <NavItem isCollapsed={isCollapsed} icon={<MessageSquare size={18} />} label="Initial Discovery" />
            <NavItem isCollapsed={isCollapsed} icon={<History size={18} />} label="Tech Stack Analysis" />
          </nav>
        </div>
      </div>

      {/* User Section */}
      <div className="mt-auto p-3 border-t border-gray-200">
        <NavItem isCollapsed={isCollapsed} icon={<Settings size={18} />} label="Settings" />
        <div className={cn("flex items-center gap-3 px-2 py-2 mt-2", isCollapsed && "justify-center")}>
          <div className="w-8 h-8 bg-emerald-200 rounded-full flex-shrink-0 flex items-center justify-center text-emerald-700 text-xs font-bold">
            AM
          </div>
          {!isCollapsed}
        </div>
      </div>
    </div>
  );
}

function NavItem({ icon, label, isCollapsed }: { icon: any; label: string; isCollapsed: boolean }) {
  return (
    <div className={cn(
      "flex items-center gap-3 px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-lg cursor-pointer transition-colors",
      isCollapsed && "justify-center"
    )}>
      <div className="flex-shrink-0">{icon}</div>
      {!isCollapsed && <span className="text-sm font-medium overflow-hidden whitespace-nowrap">{label}</span>}
    </div>
  );
}