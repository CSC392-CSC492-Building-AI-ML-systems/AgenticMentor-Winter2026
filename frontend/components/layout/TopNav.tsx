"use client";
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Terminal, Settings, User, Sun, Moon, LogOut, Home } from "lucide-react";
import { useAuthStore } from "@/store/useAuthStore";
import { getFirebaseAuth } from "@/lib/firebase";
import { fetchWithAuth } from "@/lib/api";
import LlmSettingsModal from "@/components/settings/LlmSettingsModal";
import { useLlmUiStore } from "@/store/useLlmUiStore";

export default function TopNav() {
  const [isDark, setIsDark] = useState(() =>
    typeof window !== "undefined" && localStorage.getItem("theme") === "dark"
  );
  const [showUserMenu, setShowUserMenu] = useState(false);
  const { llmModalOpen, setLlmModalOpen, bumpLlmRuntimeRefresh } = useLlmUiStore();
  const userMenuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { user, idToken, clearAuth } = useAuthStore();

  useEffect(() => {
    const dark = localStorage.getItem("theme") === "dark";
    setIsDark(dark);
  }, []);

  const toggleTheme = () => {
    const next = !isDark;
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
    setIsDark(next);
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) setShowUserMenu(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    if (idToken) {
      try {
        await fetchWithAuth("/auth/clear-llm-keys", { method: "POST", token: idToken });
      } catch {
        /* best-effort: still sign out locally */
      }
    }
    const auth = getFirebaseAuth();
    if (auth) auth.signOut();
    clearAuth();
    setShowUserMenu(false);
    router.replace("/");
  };


  return (
    <>
    <div className="h-12 border-b border-gray-300 dark:border-[#444] flex items-center justify-between px-4 sm:px-6 bg-gray-50 dark:bg-black shrink-0 transition-colors">

      {/* LEFT */}
      <div className="flex items-center gap-4">
        <Terminal size={16} className="text-black dark:text-white hidden sm:block" />
        <span className="text-xs font-bold tracking-widest text-black dark:text-white uppercase hidden sm:block">
          Command_Center
        </span>
        <div className="w-px h-4 bg-gray-300 dark:bg-[#555] hidden sm:block"></div>
        <Link href="/dashboard" className="text-gray-500 hover:text-black dark:text-gray-400 dark:hover:text-white transition-colors" title="Home">
          <Home size={14} />
        </Link>
      </div>

      {/* RIGHT */}
      <div className="flex items-center gap-4 sm:gap-6">


        {/* Theme Toggle */}
        <button onClick={toggleTheme} className="text-gray-500 hover:text-black dark:text-gray-400 dark:hover:text-white transition-colors" title="Toggle Theme">
          {isDark ? <Sun size={14} /> : <Moon size={14} />}
        </button>

        <div className="w-px h-4 bg-gray-300 dark:bg-[#555]"></div>

        {/* Status Indicator */}
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-black dark:bg-white rounded-full animate-pulse shadow-[0_0_8px_rgba(0,0,0,0.5)] dark:shadow-[0_0_8px_rgba(255,255,255,1)]"></div>
          <span className="text-[10px] text-black dark:text-white tracking-widest uppercase font-bold hidden sm:block">System Ready</span>
        </div>

        <div className="w-px h-4 bg-gray-300 dark:bg-[#555]"></div>

        {/* Settings */}
        <button
          onClick={() => setLlmModalOpen(true)}
          className="text-gray-500 hover:text-black dark:text-gray-200 dark:hover:text-white transition-colors"
          title="LLM Settings"
        >
          <Settings size={14} />
        </button>

        {/* User menu */}
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
    <LlmSettingsModal
      open={llmModalOpen}
      onClose={() => {
        setLlmModalOpen(false);
        bumpLlmRuntimeRefresh();
      }}
    />
    </>
  );
}
