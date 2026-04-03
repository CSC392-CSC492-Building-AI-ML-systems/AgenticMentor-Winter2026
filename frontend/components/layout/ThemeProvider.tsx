"use client";
import { useEffect } from "react";
import { usePathname } from "next/navigation";

export default function ThemeProvider() {
  const pathname = usePathname();

  useEffect(() => {
    const dark = localStorage.getItem("theme") === "dark";
    document.documentElement.classList.toggle("dark", dark);
  }, [pathname]);

  return null;
}
