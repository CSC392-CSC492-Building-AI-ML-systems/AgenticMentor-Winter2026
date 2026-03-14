"use client";
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Terminal, Settings, User, Download, FileText, Github, FileDown, Sun, Moon, LogOut } from "lucide-react";
import { useAuthStore } from "@/store/useAuthStore";
import { getFirebaseAuth } from "@/lib/firebase";

export default function TopNav() {
  const [showExport, setShowExport] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { user, idToken, clearAuth } = useAuthStore();

  // Theme Toggle Logic
  useEffect(() => {
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.classList.add('dark');
      setIsDark(true);
    }
  }, []);

  const toggleTheme = () => {
    document.documentElement.classList.toggle('dark');
    setIsDark(!isDark);
  };

  // Click outside logic for dropdowns
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(event.target as Node)) setShowExport(false);
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) setShowUserMenu(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    const auth = getFirebaseAuth();
    if (auth) auth.signOut();
    clearAuth();
    setShowUserMenu(false);
    router.replace("/");
  };

  return (
    <div className="h-12 border-b border-gray-300 dark:border-[#444] flex items-center justify-between px-4 sm:px-6 bg-gray-50 dark:bg-black flex-shrink-0 transition-colors">
      
      {/* LEFT SIDE: Branding & Chat/Project Name */}
      <div className="flex items-center gap-4">
        <Terminal size={16} className="text-black dark:text-white hidden sm:block" />
        <span className="text-xs font-bold tracking-widest text-black dark:text-white uppercase hidden sm:block">
          Command_Center
        </span>
        
        <div className="w-[1px] h-4 bg-gray-300 dark:bg-[#555] hidden sm:block"></div>
        
        {/* Migrated from Topbar: The Chat/Project Name */}
        <span className="text-[10px] bg-gray-200 dark:bg-[#111] border border-gray-300 dark:border-[#444] px-2 py-1 text-gray-700 dark:text-gray-300 font-bold uppercase tracking-widest transition-colors">
          Project: Auth_Gateway
        </span>
      </div>

      {/* RIGHT SIDE: Tools & Toggles */}
      <div className="flex items-center gap-4 sm:gap-6">
        
        {/* Exporter Agent Menu */}
        <div className="relative hidden sm:block" ref={exportRef}>
          <button 
            onClick={() => setShowExport(!showExport)}
            className="flex items-center gap-2 border border-gray-300 dark:border-[#555] bg-white dark:bg-[#050505] hover:border-black dark:hover:border-white text-black dark:text-white px-3 py-1 text-[10px] font-bold tracking-widest uppercase transition-colors"
          >
            <Download size={12} />
            Export
          </button>

          {showExport && (
            <div className="absolute top-full right-0 mt-2 w-56 bg-white dark:bg-black border border-gray-300 dark:border-[#555] shadow-2xl z-50 py-1 transition-colors">
              <div className="px-3 py-2 text-[9px] font-bold text-gray-500 uppercase tracking-widest border-b border-gray-200 dark:border-[#444]">
                Select_Export_Medium
              </div>
              <button className="w-full flex items-center gap-3 px-3 py-2.5 text-[10px] font-bold text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white hover:text-black transition-colors uppercase tracking-widest">
                <FileDown size={14} /> Consolidate PDF
              </button>
              <button className="w-full flex items-center gap-3 px-3 py-2.5 text-[10px] font-bold text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white hover:text-black transition-colors uppercase tracking-widest">
                <Github size={14} /> Push to GitHub README
              </button>
              <button className="w-full flex items-center gap-3 px-3 py-2.5 text-[10px] font-bold text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white hover:text-black transition-colors uppercase tracking-widest">
                <FileText size={14} /> Raw Markdown
              </button>
            </div>
          )}
        </div>

        {/* Theme Toggle (Light/Dark) */}
        <button onClick={toggleTheme} className="text-gray-500 hover:text-black dark:text-gray-400 dark:hover:text-white transition-colors" title="Toggle Theme">
          {isDark ? <Sun size={14} /> : <Moon size={14} />}
        </button>

        <div className="w-[1px] h-4 bg-gray-300 dark:bg-[#555]"></div>

        {/* Status Indicator */}
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-black dark:bg-white rounded-full animate-pulse shadow-[0_0_8px_rgba(0,0,0,0.5)] dark:shadow-[0_0_8px_rgba(255,255,255,1)]"></div>
          <span className="text-[10px] text-black dark:text-white tracking-widest uppercase font-bold hidden sm:block">System Ready</span>
        </div>
        
        <div className="w-[1px] h-4 bg-gray-300 dark:bg-[#555]"></div>

        {/* User Profile / Settings */}
        <button className="text-gray-500 hover:text-black dark:text-gray-200 dark:hover:text-white transition-colors">
          <Settings size={14} />
        </button>
        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="w-6 h-6 bg-gray-200 dark:bg-[#111] flex items-center justify-center border border-gray-300 dark:border-[#555] cursor-pointer hover:border-black dark:hover:border-white transition-colors"
            title={idToken && user?.email ? user.email : "User"}
          >
            <User size={14} className="text-black dark:text-white" />
          </button>
          {showUserMenu && (
            <div className="absolute top-full right-0 mt-2 w-48 bg-white dark:bg-black border border-gray-300 dark:border-[#555] shadow-xl z-50 py-1 transition-colors">
              {user?.email && (
                <div className="px-3 py-2 text-[10px] text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-[#444] truncate">
                  {user.email}
                </div>
              )}
              <Link href="/" className="block w-full text-left px-3 py-2 text-[10px] font-bold text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white hover:text-black transition-colors uppercase tracking-widest">
                Home
              </Link>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 text-[10px] font-bold text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-[#111] transition-colors uppercase tracking-widest"
              >
                <LogOut size={12} />
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}