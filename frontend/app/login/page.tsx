"use client";
import Link from "next/link";
import { Lock, ArrowRight, ShieldCheck, Github, Chrome } from "lucide-react";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import ThemeToggle from "@/components/layout/ThemeToggle";
import { useAuthStore } from "@/store/useAuthStore";
import { getApiUrl } from "@/lib/api";
import { formatApiError } from "@/lib/formatApiError";
import { getFirebaseAuth, googleProvider, githubProvider } from "@/lib/firebase";

type AuthMethod = "OAUTH_GITHUB" | "OAUTH_GOOGLE" | "MANUAL";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authStatus, setAuthStatus] = useState<"IDLE" | AuthMethod>("IDLE");
  const [error, setError] = useState<string | null>(null);
  const [checkingRedirect, setCheckingRedirect] = useState(true);
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const redirectError = useAuthStore((s) => s.redirectError);
  const setRedirectError = useAuthStore((s) => s.setRedirectError);

  // After mount: give AuthRedirectHandler (in layout) time to process OAuth return, then
  // if we're already logged in (persisted or just set by handler), go to dashboard.
  useEffect(() => {
    const t = setTimeout(() => {
      if (useAuthStore.getState().idToken) {
        router.replace("/dashboard");
        return;
      }
      setCheckingRedirect(false);
    }, 300);
    return () => clearTimeout(t);
  }, [router]);

  async function handleEmailPassword(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setAuthStatus("MANUAL");

    try {
      const res = await fetch(getApiUrl("/auth/login/email"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        setAuthStatus("IDLE");
        setError(formatApiError(data.detail ?? "Login failed. Check email and password."));
        return;
      }

      const idToken = data.id_token;
      if (!idToken) {
        setAuthStatus("IDLE");
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
      setAuthStatus("IDLE");
      setError("Network error. Is the backend running?");
    }
  }

  async function handleOAuthRedirect(method: "OAUTH_GOOGLE" | "OAUTH_GITHUB") {
    setError(null);
    setRedirectError(null);
    const auth = getFirebaseAuth();
    if (!auth) {
      setError("Firebase is not configured. Add NEXT_PUBLIC_FIREBASE_* env vars.");
      return;
    }
    setAuthStatus(method);
    const provider = method === "OAUTH_GOOGLE" ? googleProvider : githubProvider;
    try {
      const result = await auth.signInWithPopup(provider);
      const u = result.user;
      if (!u) {
        setAuthStatus("IDLE");
        setError("Sign-in did not return a user.");
        return;
      }
      const idToken = await u.getIdToken();
      setAuth(idToken, {
        uid: u.uid,
        email: u.email ?? null,
        name: u.displayName ?? null,
        picture: u.photoURL ?? null,
      });
      router.replace("/dashboard");
    } catch (err: unknown) {
      setAuthStatus("IDLE");
      const msg = err && typeof err === "object" && "message" in err ? String((err as { message: string }).message) : "Sign-in failed.";
      setError(msg);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-black text-black dark:text-white font-mono selection:bg-gray-300 dark:selection:bg-gray-200 selection:text-black p-6 transition-colors">
      <div className="w-full max-w-md border border-gray-300 dark:border-[#444] bg-gray-50 dark:bg-[#050505] p-8 relative transition-colors shadow-sm dark:shadow-none">
        <div className="absolute top-0 left-0 w-full h-1 bg-black dark:bg-white transition-colors" />
        <div className="flex justify-between items-center mb-8 border-b border-gray-300 dark:border-[#444] pb-4 transition-colors">
          <div className="flex items-center gap-3">
            <Lock size={16} className="text-black dark:text-white transition-colors" />
            <span className="text-xs font-bold tracking-widest uppercase text-black dark:text-white transition-colors">Identity_Gateway</span>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <span className="text-[10px] text-gray-500 dark:text-gray-200 font-bold transition-colors">SECURE_TUNNEL</span>
          </div>
        </div>

        {(error || redirectError) && (
          <div className="mb-4 p-3 border border-red-400 dark:border-red-600 bg-red-50 dark:bg-red-950/50 text-red-700 dark:text-red-300 text-xs">
            {error || redirectError}
            {redirectError && (
              <button type="button" onClick={() => setRedirectError(null)} className="ml-2 underline">
                Dismiss
              </button>
            )}
          </div>
        )}

        {checkingRedirect ? (
          <div className="py-12 flex flex-col items-center justify-center text-center space-y-6">
            <ShieldCheck size={32} className="text-black dark:text-white animate-pulse transition-colors" />
            <p className="text-xs text-black dark:text-white font-bold uppercase tracking-widest transition-colors">
              Completing sign-in...
            </p>
          </div>
        ) : authStatus !== "IDLE" ? (
          <div className="py-12 flex flex-col items-center justify-center text-center space-y-6">
            <ShieldCheck size={32} className="text-black dark:text-white animate-pulse transition-colors" />
            <div className="space-y-2">
              <p className="text-xs text-black dark:text-white font-bold uppercase tracking-widest transition-colors">
                {authStatus === "MANUAL" ? "Verifying Root Credentials..." : `Executing ${authStatus.replace("_", " ")}...`}
              </p>
              <p className="text-[10px] text-gray-500 dark:text-gray-200 transition-colors">ESTABLISHING ENCRYPTED SESSION [OK]</p>
              <p className="text-[10px] text-gray-500 dark:text-gray-200 transition-colors">RESTORING SAVED WORKSPACES [OK]</p>
              <p className="text-[10px] text-gray-500 dark:text-gray-200 animate-pulse transition-colors">SYNCING ARTIFACT_HISTORY...</p>
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            <div className="space-y-3">
              <button
                type="button"
                onClick={() => handleOAuthRedirect("OAUTH_GITHUB")}
                className="w-full border border-gray-300 dark:border-[#555] bg-white dark:bg-black text-black dark:text-white hover:bg-gray-100 dark:hover:bg-white dark:hover:text-black font-bold tracking-widest uppercase text-xs py-3 flex items-center justify-center gap-3 transition-colors"
              >
                <Github size={16} />
                Init_GitHub_OAuth
              </button>
              <button
                type="button"
                onClick={() => handleOAuthRedirect("OAUTH_GOOGLE")}
                className="w-full border border-gray-300 dark:border-[#555] bg-white dark:bg-black text-black dark:text-white hover:bg-gray-100 dark:hover:bg-white dark:hover:text-black font-bold tracking-widest uppercase text-xs py-3 flex items-center justify-center gap-3 transition-colors"
              >
                <Chrome size={16} />
                Init_Google_OAuth
              </button>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex-1 border-t border-gray-300 dark:border-[#444] transition-colors" />
              <span className="text-[10px] text-gray-500 dark:text-gray-200 font-bold tracking-widest uppercase transition-colors">Or_Manual_Entry</span>
              <div className="flex-1 border-t border-gray-300 dark:border-[#444] transition-colors" />
            </div>

            <form onSubmit={handleEmailPassword} className="space-y-5">
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

        <div className="mt-8 pt-4 border-t border-gray-300 dark:border-[#444] flex flex-wrap justify-between items-center gap-2 text-[10px] text-gray-500 dark:text-gray-200 font-bold transition-colors">
          <div className="flex items-center gap-4">
            <Link href="/" className="hover:text-black dark:hover:text-white transition-colors uppercase tracking-widest">
              [&lt;-] Abort_Sequence
            </Link>
            <Link href="/signup" className="hover:text-black dark:hover:text-white transition-colors uppercase tracking-widest">
              Create_Account
            </Link>
          </div>
          <span className="text-black dark:text-white transition-colors">V_4.0.1</span>
        </div>
      </div>
    </div>
  );
}
