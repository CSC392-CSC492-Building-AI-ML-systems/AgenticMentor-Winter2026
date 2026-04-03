"use client";
import { useState, useRef, KeyboardEvent } from "react";
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
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    // Auto-resize
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  };

  const handleSend = () => {
    if (value.trim()) {
      const isContinue = CONTINUE_PHRASES.has(value.trim().toLowerCase());
      onSend(value, AUTO_AGENT, isContinue);
      setValue("");
      // Reset height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t-2 border-gray-200 dark:border-[#333] bg-gray-50 dark:bg-[#0a0a0a] px-6 pb-6 pt-3 flex-shrink-0 transition-colors">
      <div className="flex justify-end mb-2">
        <span className="text-[9px] text-gray-400 dark:text-gray-600 font-mono">Shift+Enter for new line</span>
      </div>

      <div className="border-2 border-gray-300 dark:border-[#333] flex focus-within:border-black dark:focus-within:border-white transition-colors bg-white dark:bg-[#111]">
        <div className="px-4 flex items-start pt-[14px] text-black dark:text-white font-bold text-sm border-r-2 border-gray-300 dark:border-[#333] transition-colors flex-shrink-0">&gt;_</div>

        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Execute prompt"
          rows={1}
          className="flex-1 bg-transparent border-none text-[13px] text-black dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-600 px-4 py-[13px] focus:outline-none font-mono resize-none leading-[1.5]"
          style={{ maxHeight: "160px", overflowY: "auto" }}
        />

        <button
          onClick={handleSend}
          disabled={!value.trim()}
          className="bg-black dark:bg-white text-white dark:text-black px-5 flex items-start pt-[13px] justify-center hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-30 flex-shrink-0 border-l-2 border-gray-300 dark:border-[#333] self-stretch"
        >
          <ArrowUpRight size={18} strokeWidth={3} />
        </button>
      </div>
    </div>
  );
}
