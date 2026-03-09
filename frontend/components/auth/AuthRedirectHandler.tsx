"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";
import { getFirebaseAuth } from "@/lib/firebase";

/**
 * Runs once on app load to handle OAuth redirect (Google/GitHub).
 * When the user returns from the provider, we set auth and send them to dashboard.
 * Mounted in root layout so it works whether they land on / or /login.
 */
export default function AuthRedirectHandler() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const setRedirectError = useAuthStore((s) => s.setRedirectError);
  const didRun = useRef(false);

  useEffect(() => {
    if (didRun.current) return;
    didRun.current = true;

    const auth = getFirebaseAuth();
    if (!auth) return;

    auth
      .getRedirectResult()
      .then((result) => {
        const u = result.user;
        if (!u) return;
        u.getIdToken()
          .then((idToken) => {
            setAuth(idToken, {
              uid: u.uid,
              email: u.email ?? null,
              name: u.displayName ?? null,
              picture: u.photoURL ?? null,
            });
            router.replace("/dashboard");
          })
          .catch((err: unknown) => {
            const msg = err && typeof err === "object" && "message" in err ? String((err as { message: string }).message) : "Failed to get token.";
            setRedirectError(msg);
          });
      })
      .catch((err: unknown) => {
        const msg = err && typeof err === "object" && "message" in err ? String((err as { message: string }).message) : "Sign-in was cancelled or failed.";
        setRedirectError(msg);
      });
  }, [router, setAuth, setRedirectError]);

  return null;
}
