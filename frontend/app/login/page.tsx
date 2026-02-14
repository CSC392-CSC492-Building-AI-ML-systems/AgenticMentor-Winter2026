"use client";
import Link from "next/link";
import { Lock, ArrowRight, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const router = useRouter();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setIsAuthenticating(true);
    
    // Simulate backend auth delay, then redirect to dashboard
    setTimeout(() => {
      router.push("/dashboard");
    }, 1500);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white font-mono selection:bg-gray-700 selection:text-white p-6">
      
      <div className="w-full max-w-md border border-[#333] bg-[#050505] p-8 relative">
        {/* Terminal Header */}
        <div className="absolute top-0 left-0 w-full h-1 bg-white"></div>
        <div className="flex justify-between items-center mb-10 border-b border-[#333] pb-4">
          <div className="flex items-center gap-3">
            <Lock size={16} className="text-gray-400" />
            <span className="text-xs font-bold tracking-widest uppercase">Identity_Gateway</span>
          </div>
          <span className="text-[10px] text-gray-500">SECURE_TUNNEL</span>
        </div>

        {isAuthenticating ? (
          // Authenticating State
          <div className="py-12 flex flex-col items-center justify-center text-center space-y-6">
            <ShieldCheck size={32} className="text-white animate-pulse" />
            <div className="space-y-2">
              <p className="text-xs text-gray-400 uppercase tracking-widest">Verifying Credentials...</p>
              <p className="text-[10px] text-gray-600">ESTABLISHING ENCRYPTED SESSION</p>
            </div>
          </div>
        ) : (
          // Login Form
          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-gray-400 tracking-widest uppercase">Operator_ID</label>
              <div className="border border-[#444] bg-black flex items-center focus-within:border-white transition-colors">
                <span className="pl-3 text-gray-500 font-bold">&gt;_</span>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-transparent border-none text-sm text-white px-3 py-3 focus:outline-none placeholder:text-[#333]"
                  placeholder="admin_root"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-bold text-gray-400 tracking-widest uppercase">Access_Key</label>
              <div className="border border-[#444] bg-black flex items-center focus-within:border-white transition-colors">
                <span className="pl-3 text-gray-500 font-bold">***</span>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-transparent border-none text-sm text-white px-3 py-3 focus:outline-none placeholder:text-[#333]"
                  placeholder="••••••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full bg-white text-black font-bold tracking-widest uppercase text-sm py-4 mt-4 flex items-center justify-center gap-3 hover:bg-gray-200 transition-colors"
            >
              Execute_Auth
              <ArrowRight size={16} strokeWidth={3} />
            </button>
          </form>
        )}

        <div className="mt-8 pt-4 border-t border-[#333] flex justify-between items-center text-[10px] text-gray-500">
          <Link href="/" className="hover:text-white transition-colors uppercase tracking-widest">
            [&lt;-] Abort_Sequence
          </Link>
          <span>V_4.0.1</span>
        </div>
      </div>
    </div>
  );
}