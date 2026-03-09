"use client";

import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { useAuthStore } from "@/store/useAuthStore";

/**
 * Links to /dashboard if logged in, otherwise /login (so "Authenticate" respects persisted state).
 */
export default function AuthLink() {
  const idToken = useAuthStore((s) => s.idToken);
  const href = idToken ? "/dashboard" : "/login";
  const label = idToken ? "Go to Dashboard" : "Authenticate";

  return (
    <Link
      href={href}
      className="flex-1 sm:max-w-[220px] border border-gray-300 dark:border-[#555] bg-gray-50 dark:bg-[#050505] hover:border-black dark:hover:border-white transition-all p-4 flex flex-col items-start group relative"
    >
      <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-black dark:border-white opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-black dark:border-white opacity-0 group-hover:opacity-100 transition-opacity" />
      <ShieldAlert size={14} className="text-gray-500 dark:text-gray-200 mb-3 group-hover:text-black dark:group-hover:text-white transition-colors" />
      <span className="text-[10px] text-gray-500 dark:text-gray-200 tracking-widest uppercase mb-1 font-bold transition-colors">Req_Access</span>
      <span className="text-sm font-bold text-black dark:text-white uppercase tracking-widest transition-colors">{label}</span>
    </Link>
  );
}
