"use client";
import { useState, KeyboardEvent, useRef, useEffect } from "react";
import { Send, Mic, Paperclip, Bot, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const AGENTS = [
  { id: "requirements", name: "Requirements Collector Agent", color: "purple" },
  { id: "project_architect", name: "Project Architect Agent", color: "blue" },
  { id: "execution_planner", name: "Execution Planner Agent", color: "red" },
  { id: "mockup_rendering", name: "Mockup Rendering Agent", color: "orange" },
  { id: "exporter", name: "Exporter Agent", color: "green" },
];

interface ChatInputProps {
  // We now pass the whole agent object so the Window knows who is talking
  onSend: (text: string, agent: typeof AGENTS[0]) => void;
}

export default function ChatInput({ onSend }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [selectedAgent, setSelectedAgent] = useState(AGENTS[0]);
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSend = () => {
    if (value.trim()) {
      onSend(value, selectedAgent);
      setValue("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-full max-w-3xl px-4 z-20">
      <div className="bg-white rounded-2xl shadow-xl border border-gray-200 p-2">
        <div className="px-2 pt-1 pb-2 flex relative" ref={menuRef}>
          <button 
            onClick={() => setShowMenu(!showMenu)}
            className={cn(
              "text-[11px] font-bold px-2 py-1 rounded-md flex items-center gap-1.5 border transition-all uppercase tracking-tight",
              selectedAgent.color === "purple" ? "bg-purple-50 text-purple-700 border-purple-100" :
              selectedAgent.color === "blue" ? "bg-blue-50 text-blue-700 border-blue-100" :
              selectedAgent.color === "red" ? "bg-red-50 text-red-700 border-red-100" :
              selectedAgent.color === "orange" ? "bg-orange-50 text-orange-700 border-orange-100" :
              "bg-green-50 text-green-700 border-green-100"
            )}
          >
            <Bot size={13} />
            {selectedAgent.name}
            <ChevronDown size={12} className={cn("transition-transform opacity-60", showMenu && "rotate-180")} />
          </button>

          {showMenu && (
            <div className="absolute bottom-full mb-2 left-2 w-64 bg-white border border-gray-200 rounded-xl shadow-2xl z-50 py-2">
              {AGENTS.map((agent) => (
                <button
                  key={agent.id}
                  onClick={() => { setSelectedAgent(agent); setShowMenu(false); }}
                  className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 text-sm text-gray-700 transition-colors"
                >
                  <div className={cn("w-2 h-2 rounded-full", 
                    agent.color === "purple" ? "bg-purple-500" : 
                    agent.color === "blue" ? "bg-blue-500" : 
                    agent.color === "red" ? "bg-red-500" : 
                    agent.color === "orange" ? "bg-orange-500" : "bg-green-500"
                  )} />
                  {agent.name}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-end gap-2 px-2 pb-1">
          <button className="p-2 text-gray-400 hover:text-gray-600 rounded-full mb-1"><Paperclip size={20} /></button>
          <textarea
            className="flex-1 max-h-32 bg-transparent border-none focus:ring-0 resize-none py-3 text-sm outline-none"
            placeholder={`Ask ${selectedAgent.name}...`}
            rows={1}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <div className="flex items-center gap-2 mb-1">
             <button className="p-2 text-gray-400 hover:text-gray-600 rounded-full"><Mic size={20} /></button>
             <button onClick={handleSend} className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm">
                <Send size={18} />
             </button>
          </div>
        </div>
      </div>
    </div>
  );
}