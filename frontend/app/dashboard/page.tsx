import Sidebar from "@/components/layout/Sidebar";
import ProjectCard from "@/components/dashboard/ProjectCard";
import { Plus, Search, Filter } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <Sidebar />

      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="px-8 py-6 bg-white border-b border-gray-200 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Your Projects</h1>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
              <input 
                type="text" 
                placeholder="Search..." 
                className="pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none w-48 lg:w-64"
              />
            </div>
            
            <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-shadow">
              <Plus size={16} />
              New Project
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Active Workspace</h2>
            <button className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800">
              <Filter size={14} />
              Sort by: Recent
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Link href="/project/1"><ProjectCard title="CRM System" description="Internal CRM planning" lastEdited="2h ago" status="Active" color="bg-blue-600" /></Link>
            <Link href="/project/2"><ProjectCard title="Marketing Site" description="Landing page system design" lastEdited="Yesterday" status="Active" color="bg-purple-600" /></Link>
          </div>
        </div>
      </main>
    </div>
  );
}