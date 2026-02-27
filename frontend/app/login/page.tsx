"use client";
import Link from "next/link";
import { Lock, ArrowRight, ShieldCheck, Github, Chrome } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import ThemeToggle from "@/components/layout/ThemeToggle";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authStatus, setAuthStatus] = useState<"IDLE" | "OAUTH_GITHUB" | "OAUTH_GOOGLE" | "MANUAL">("IDLE");
  const router = useRouter();

  const handleLogin = (e?: React.FormEvent, method: "OAUTH_GITHUB" | "OAUTH_GOOGLE" | "MANUAL" = "MANUAL") => {
    if (e) e.preventDefault();
    setAuthStatus(method);
    
    // Simulate backend OAuth handshake and workspace sync, then redirect to dashboard
    setTimeout(() => {
      router.push("/dashboard");
    }, 2000);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-black text-black dark:text-white font-mono selection:bg-gray-300 dark:selection:bg-gray-200 selection:text-black p-6 transition-colors">
      
      <div className="w-full max-w-md border border-gray-300 dark:border-[#444] bg-gray-50 dark:bg-[#050505] p-8 relative transition-colors shadow-sm dark:shadow-none">
        {/* Terminal Top Accent - Inverts to black in light mode */}
        <div className="absolute top-0 left-0 w-full h-1 bg-black dark:bg-white transition-colors"></div>
        
        {/* Header */}
        <div className="flex justify-between items-center mb-8 border-b border-gray-300 dark:border-[#444] pb-4 transition-colors">
          <div className="flex items-center gap-3">
            <Lock size={16} className="text-black dark:text-white transition-colors" />
            <span className="text-xs font-bold tracking-widest uppercase text-black dark:text-white transition-colors">Identity_Gateway</span>
          </div>

          {/* ADDED THE TOGGLE HERE NEXT TO THE TEXT */}
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <span className="text-[10px] text-gray-500 dark:text-gray-200 font-bold transition-colors">SECURE_TUNNEL</span>
          </div>
        </div>

        {authStatus !== "IDLE" ? (
          // Milestone 2: Authenticating & Syncing State
          <div className="py-12 flex flex-col items-center justify-center text-center space-y-6">
            <ShieldCheck size={32} className="text-black dark:text-white animate-pulse transition-colors" />
            <div className="space-y-2">
              <p className="text-xs text-black dark:text-white font-bold uppercase tracking-widest transition-colors">
                {authStatus === "MANUAL" ? "Verifying Root Credentials..." : `Executing ${authStatus.replace('_', ' ')}...`}
              </p>
              <p className="text-[10px] text-gray-500 dark:text-gray-200 transition-colors">ESTABLISHING ENCRYPTED SESSION [OK]</p>
              <p className="text-[10px] text-gray-500 dark:text-gray-200 transition-colors">RESTORING SAVED WORKSPACES [OK]</p>
              <p className="text-[10px] text-gray-500 dark:text-gray-200 animate-pulse transition-colors">SYNCING ARTIFACT_HISTORY...</p>
            </div>
          </div>
        ) : (
          // Login Options
          <div className="space-y-8">
            
            {/* OAuth Providers */}
            <div className="space-y-3">
              <button 
                onClick={() => handleLogin(undefined, "OAUTH_GITHUB")}
                className="w-full border border-gray-300 dark:border-[#555] bg-white dark:bg-black text-black dark:text-white hover:bg-gray-100 dark:hover:bg-white dark:hover:text-black font-bold tracking-widest uppercase text-xs py-3 flex items-center justify-center gap-3 transition-colors"
              >
                <Github size={16} />
                Init_GitHub_OAuth
              </button>
              
              <button 
                onClick={() => handleLogin(undefined, "OAUTH_GOOGLE")}
                className="w-full border border-gray-300 dark:border-[#555] bg-white dark:bg-black text-black dark:text-white hover:bg-gray-100 dark:hover:bg-white dark:hover:text-black font-bold tracking-widest uppercase text-xs py-3 flex items-center justify-center gap-3 transition-colors"
              >
                <Chrome size={16} />
                Init_Google_OAuth
              </button>
            </div>

            {/* Visual Divider */}
            <div className="flex items-center gap-4">
              <div className="flex-1 border-t border-gray-300 dark:border-[#444] transition-colors"></div>
              <span className="text-[10px] text-gray-500 dark:text-gray-200 font-bold tracking-widest uppercase transition-colors">Or_Manual_Entry</span>
              <div className="flex-1 border-t border-gray-300 dark:border-[#444] transition-colors"></div>
            </div>

            {/* Manual Form */}
            <form onSubmit={(e) => handleLogin(e, "MANUAL")} className="space-y-5">
              <div className="space-y-2">
                <label className="text-[10px] font-bold text-black dark:text-white tracking-widest uppercase transition-colors">Username</label>
                <div className="border border-gray-300 dark:border-[#555] bg-white dark:bg-black flex items-center focus-within:border-black dark:focus-within:border-white transition-colors">
                  <span className="pl-3 text-black dark:text-white font-bold transition-colors">&gt;_</span>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full bg-transparent border-none text-sm text-black dark:text-white px-3 py-3 focus:outline-none placeholder:text-gray-400 font-bold transition-colors"
                    placeholder="your_username_name"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-bold text-black dark:text-white tracking-widest uppercase transition-colors">Password</label>
                <div className="border border-gray-300 dark:border-[#555] bg-white dark:bg-black flex items-center focus-within:border-black dark:focus-within:border-white transition-colors">
                  <span className="pl-3 text-black dark:text-white font-bold transition-colors">***</span>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-transparent border-none text-sm text-black dark:text-white px-3 py-3 focus:outline-none placeholder:text-gray-400 font-bold transition-colors"
                    placeholder="••••••••••••"
                  />
                </div>
              </div>

              {/* Submit Button - Inverts to solid black in light mode, solid white in dark mode */}
              <button
                type="submit"
                className="w-full bg-black dark:bg-white text-white dark:text-black font-bold tracking-widest uppercase text-sm py-4 mt-2 flex items-center justify-center gap-3 hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors"
              >
                Execute_Auth
                <ArrowRight size={16} strokeWidth={3} />
              </button>
            </form>
          </div>
        )}

        {/* Footer */}
        <div className="mt-8 pt-4 border-t border-gray-300 dark:border-[#444] flex justify-between items-center text-[10px] text-gray-500 dark:text-gray-200 font-bold transition-colors">
          <Link href="/" className="hover:text-black dark:hover:text-white transition-colors uppercase tracking-widest">
            [&lt;-] Abort_Sequence
          </Link>
          <span className="text-black dark:text-white transition-colors">V_4.0.1</span>
        </div>
      </div>
    </div>
  );
}