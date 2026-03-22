"use client";
import { useState } from "react";
import { Sun, Moon } from "lucide-react";

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(() =>
    typeof window !== "undefined" && localStorage.getItem("theme") === "dark"
  );

  const toggleTheme = () => {
    const next = !isDark;
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
    setIsDark(next);
  };

  return (
    <button 
      onClick={toggleTheme} 
      className="text-gray-500 hover:text-black dark:text-gray-400 dark:hover:text-white transition-colors p-2" 
      title="Toggle Theme"
    >
      {isDark ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
}