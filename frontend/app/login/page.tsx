"use client";
import Link from "next/link";
import { Lock, ArrowRight, ShieldCheck, Github, Chrome } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";

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
    <div className="min-h-screen flex items-center justify-center bg-black text-white font-mono selection:bg-gray-200 selection:text-black p-6">
      
      <div className="w-full max-w-md border border-[#444] bg-[#050505] p-8 relative">
        {/* Terminal Top Accent */}
        <div className="absolute top-0 left-0 w-full h-1 bg-white"></div>
        
        {/* Header */}
        <div className="flex justify-between items-center mb-8 border-b border-[#444] pb-4">
          <div className="flex items-center gap-3">
            <Lock size={16} className="text-white" />
            <span className="text-xs font-bold tracking-widest uppercase text-white">Identity_Gateway</span>
          </div>
          <span className="text-[10px] text-gray-200 font-bold">SECURE_TUNNEL</span>
        </div>

        {authStatus !== "IDLE" ? (
          // Milestone 2: Authenticating & Syncing State
          <div className="py-12 flex flex-col items-center justify-center text-center space-y-6">
            <ShieldCheck size={32} className="text-white animate-pulse" />
            <div className="space-y-2">
              <p className="text-xs text-white font-bold uppercase tracking-widest">
                {authStatus === "MANUAL" ? "Verifying Root Credentials..." : `Executing ${authStatus.replace('_', ' ')}...`}
              </p>
              <p className="text-[10px] text-gray-200">ESTABLISHING ENCRYPTED SESSION [OK]</p>
              <p className="text-[10px] text-gray-200">RESTORING SAVED WORKSPACES [OK]</p>
              <p className="text-[10px] text-gray-200 animate-pulse">SYNCING ARTIFACT_HISTORY...</p>
            </div>
          </div>
        ) : (
          // Login Options
          <div className="space-y-8">
            
            {/* OAuth Providers */}
            <div className="space-y-3">
              <button 
                onClick={() => handleLogin(undefined, "OAUTH_GITHUB")}
                className="w-full border border-[#555] bg-black text-white hover:bg-white hover:text-black font-bold tracking-widest uppercase text-xs py-3 flex items-center justify-center gap-3 transition-colors"
              >
                <Github size={16} />
                Init_GitHub_OAuth
              </button>
              
              <button 
                onClick={() => handleLogin(undefined, "OAUTH_GOOGLE")}
                className="w-full border border-[#555] bg-black text-white hover:bg-white hover:text-black font-bold tracking-widest uppercase text-xs py-3 flex items-center justify-center gap-3 transition-colors"
              >
                <Chrome size={16} />
                Init_Google_OAuth
              </button>
            </div>

            {/* Visual Divider */}
            <div className="flex items-center gap-4">
              <div className="flex-1 border-t border-[#444]"></div>
              <span className="text-[10px] text-gray-200 font-bold tracking-widest uppercase">Or_Manual_Entry</span>
              <div className="flex-1 border-t border-[#444]"></div>
            </div>

            {/* Manual Form */}
            <form onSubmit={(e) => handleLogin(e, "MANUAL")} className="space-y-5">
              <div className="space-y-2">
                <label className="text-[10px] font-bold text-white tracking-widest uppercase">Username</label>
                <div className="border border-[#555] bg-black flex items-center focus-within:border-white transition-colors">
                  <span className="pl-3 text-white font-bold">&gt;_</span>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full bg-transparent border-none text-sm text-white px-3 py-3 focus:outline-none placeholder:text-gray-400 font-bold"
                    placeholder="your_username_name"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-bold text-white tracking-widest uppercase">Password</label>
                <div className="border border-[#555] bg-black flex items-center focus-within:border-white transition-colors">
                  <span className="pl-3 text-white font-bold">***</span>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-transparent border-none text-sm text-white px-3 py-3 focus:outline-none placeholder:text-gray-400 font-bold"
                    placeholder="••••••••••••"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full bg-white text-black font-bold tracking-widest uppercase text-sm py-4 mt-2 flex items-center justify-center gap-3 hover:bg-gray-200 transition-colors"
              >
                Execute_Auth
                <ArrowRight size={16} strokeWidth={3} />
              </button>
            </form>
          </div>
        )}

        {/* Footer */}
        <div className="mt-8 pt-4 border-t border-[#444] flex justify-between items-center text-[10px] text-gray-200 font-bold">
          <Link href="/" className="hover:text-white transition-colors uppercase tracking-widest">
            [&lt;-] Abort_Sequence
          </Link>
          <span className="text-white">V_4.0.1</span>
        </div>
      </div>
    </div>
  );
}