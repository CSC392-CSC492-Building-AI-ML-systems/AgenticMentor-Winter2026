"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const idToken = useAuthStore((s) => s.idToken);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      const token = useAuthStore.getState().idToken;
      if (!token) router.replace("/login");
      setChecked(true);
    }, 50);
    return () => clearTimeout(t);
  }, [router]);

  if (!checked || !idToken) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white dark:bg-black text-black dark:text-white font-mono text-xs uppercase tracking-widest">
        Verifying session...
      </div>
    );
  }

  return <>{children}</>;
}
