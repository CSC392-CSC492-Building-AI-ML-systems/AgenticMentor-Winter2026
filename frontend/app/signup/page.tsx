"use client";
import Link from "next/link";
import { Lock, ArrowRight, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import ThemeToggle from "@/components/layout/ThemeToggle";
import { useAuthStore } from "@/store/useAuthStore";
import { getApiUrl } from "@/lib/api";
import { formatApiError } from "@/lib/formatApiError";

export default function SignUpPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);

  async function handleSignUp(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setLoading(true);

    try {
      const res = await fetch(getApiUrl("/auth/signup/email"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        setLoading(false);
        setError(formatApiError(data.detail ?? "Sign up failed."));
        return;
      }

      const idToken = data.id_token;
      if (!idToken) {
        setLoading(false);
        setError("Invalid response from server.");
        return;
      }

      setAuth(idToken, {
        uid: data.user_id || "",
        email: data.email ?? email,
        name: null,
        picture: null,
      });
      router.push("/dashboard");
    } catch (err) {
      setLoading(false);
      setError("Network error. Is the backend running?");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-black text-black dark:text-white font-mono selection:bg-gray-300 dark:selection:bg-gray-200 selection:text-black p-6 transition-colors">
      <div className="w-full max-w-md border border-gray-300 dark:border-[#444] bg-gray-50 dark:bg-[#050505] p-8 relative transition-colors shadow-sm dark:shadow-none">
        <div className="absolute top-0 left-0 w-full h-1 bg-black dark:bg-white transition-colors" />
        <div className="flex justify-between items-center mb-8 border-b border-gray-300 dark:border-[#444] pb-4 transition-colors">
          <div className="flex items-center gap-3">
            <Lock size={16} className="text-black dark:text-white transition-colors" />
            <span className="text-xs font-bold tracking-widest uppercase text-black dark:text-white transition-colors">Create_Account</span>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <span className="text-[10px] text-gray-500 dark:text-gray-200 font-bold transition-colors">SECURE_TUNNEL</span>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 border border-red-400 dark:border-red-600 bg-red-50 dark:bg-red-950/50 text-red-700 dark:text-red-300 text-xs">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center text-center space-y-6">
            <ShieldCheck size={32} className="text-black dark:text-white animate-pulse transition-colors" />
            <p className="text-xs text-black dark:text-white font-bold uppercase tracking-widest transition-colors">
              Creating account...
            </p>
          </div>
        ) : (
          <form onSubmit={handleSignUp} className="space-y-5">
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-black dark:text-white tracking-widest uppercase transition-colors">Email</label>
              <div className="border border-gray-300 dark:border-[#555] bg-white dark:bg-black flex items-center focus-within:border-black dark:focus-within:border-white transition-colors">
                <span className="pl-3 text-black dark:text-white font-bold transition-colors">&gt;_</span>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-transparent border-none text-sm text-black dark:text-white px-3 py-3 focus:outline-none placeholder:text-gray-400 font-bold transition-colors"
                  placeholder="you@example.com"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-black dark:text-white tracking-widest uppercase transition-colors">Password (min 6)</label>
              <div className="border border-gray-300 dark:border-[#555] bg-white dark:bg-black flex items-center focus-within:border-black dark:focus-within:border-white transition-colors">
                <span className="pl-3 text-black dark:text-white font-bold transition-colors">***</span>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-transparent border-none text-sm text-black dark:text-white px-3 py-3 focus:outline-none placeholder:text-gray-400 font-bold transition-colors"
                  placeholder="••••••••••••"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-black dark:text-white tracking-widest uppercase transition-colors">Confirm Password</label>
              <div className="border border-gray-300 dark:border-[#555] bg-white dark:bg-black flex items-center focus-within:border-black dark:focus-within:border-white transition-colors">
                <span className="pl-3 text-black dark:text-white font-bold transition-colors">***</span>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full bg-transparent border-none text-sm text-black dark:text-white px-3 py-3 focus:outline-none placeholder:text-gray-400 font-bold transition-colors"
                  placeholder="••••••••••••"
                />
              </div>
            </div>
            <button
              type="submit"
              className="w-full bg-black dark:bg-white text-white dark:text-black font-bold tracking-widest uppercase text-sm py-4 mt-2 flex items-center justify-center gap-3 hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors"
            >
              Create_Account
              <ArrowRight size={16} strokeWidth={3} />
            </button>
          </form>
        )}

        <div className="mt-8 pt-4 border-t border-gray-300 dark:border-[#444] flex flex-wrap justify-between items-center gap-2 text-[10px] text-gray-500 dark:text-gray-200 font-bold transition-colors">
          <div className="flex items-center gap-4">
            <Link href="/" className="hover:text-black dark:hover:text-white transition-colors uppercase tracking-widest">
              [&lt;-] Abort_Sequence
            </Link>
            <Link href="/login" className="hover:text-black dark:hover:text-white transition-colors uppercase tracking-widest">
              Already_Have_Account
            </Link>
          </div>
          <span className="text-black dark:text-white transition-colors">V_4.0.1</span>
        </div>
      </div>
    </div>
  );
}
