"use client";
import { useState, useEffect } from "react";
import { Sun, Moon } from "lucide-react";

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(false);

  // Initialize theme based on current HTML class or system preference
  useEffect(() => {
    document.documentElement.classList.remove('dark');
    setIsDark(false);
  }, []);

  const toggleTheme = () => {
    document.documentElement.classList.toggle('dark');
    setIsDark(!isDark);
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