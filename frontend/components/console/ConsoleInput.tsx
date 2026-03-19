"use client";
import { useState, KeyboardEvent } from "react";
import { ArrowUpRight } from "lucide-react";

const AUTO_AGENT = { id: "auto", name: "Orchestrator", color: "white" };

const CONTINUE_PHRASES = new Set([
  "continue", "continue please", "continue to the next step",
  "go to the next step", "move on", "proceed", "next", "next step",
  "looks good continue", "this looks good continue", "approved continue",
]);

interface ConsoleInputProps {
  onSend: (text: string, agent: typeof AUTO_AGENT, switchTab?: boolean) => void;
}

export default function ConsoleInput({ onSend }: ConsoleInputProps) {
  const [value, setValue] = useState("");

  const handleSend = () => {
    if (value.trim()) {
      const isContinue = CONTINUE_PHRASES.has(value.trim().toLowerCase());
      onSend(value, AUTO_AGENT, isContinue);
      setValue("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t-2 border-gray-200 dark:border-[#333] bg-gray-50 dark:bg-[#0a0a0a] flex flex-col justify-end px-6 pb-6 pt-3 flex-shrink-0 relative transition-colors">
      <div className="flex justify-between items-end mb-3">
        <div className="flex gap-4 text-[11px] text-gray-500 dark:text-gray-500 font-medium">
          <button className="hover:text-black dark:hover:text-white transition-colors flex items-center gap-1.5" onClick={() => setValue("/sequence ")}>
            <span className="text-gray-400 dark:text-gray-500 text-[8px]">●</span> /sequence
          </button>
          <button className="hover:text-black dark:hover:text-white transition-colors flex items-center gap-1.5" onClick={() => setValue("/wireframe ")}>
            <span className="text-gray-400 dark:text-gray-500 text-[8px]">●</span> /wireframe
          </button>
        </div>
      </div>

      <div className="border-2 border-gray-300 dark:border-[#333] flex items-stretch focus-within:border-black dark:focus-within:border-white transition-colors bg-white dark:bg-[#111]">
        <div className="px-4 flex items-center justify-center text-black dark:text-white font-bold text-sm border-r-2 border-gray-300 dark:border-[#333] transition-colors">&gt;_</div>

        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Execute prompt for Orchestrator..."
          className="flex-1 bg-transparent border-none text-[13px] text-black dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-600 px-4 py-4 focus:outline-none font-mono"
        />

        <button
          onClick={handleSend}
          disabled={!value.trim()}
          className="bg-black dark:bg-white text-white dark:text-black px-5 flex items-center justify-center hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-30 flex-shrink-0 border-l-2 border-gray-300 dark:border-[#333]"
        >
          <ArrowUpRight size={18} strokeWidth={3} />
        </button>
      </div>
    </div>
  );
}
