"use client";
import { useState, KeyboardEvent } from "react"; // Added KeyboardEvent for "Enter" support
import { Send, Mic, Paperclip, X, Bot } from "lucide-react";

// 1. Define the Interface
interface ChatInputProps {
  onSend: (text: string) => void;
}

// 2. Apply the Interface to the component
export default function ChatInput({ onSend }: ChatInputProps) {
  const [value, setValue] = useState("");

  const handleSend = () => {
    if (value.trim()) {
      onSend(value);
      setValue(""); // Clear input after sending
    }
  };

  // 3. Add "Enter" to send logic (but Shift+Enter for new line)
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-full max-w-3xl px-4 z-20">
      <div className="bg-white rounded-2xl shadow-xl border border-gray-200 p-2">
        
        {/* Agent Pill */}
        <div className="px-2 pt-1 pb-2 flex">
          <div className="bg-purple-50 text-purple-700 text-xs font-medium px-2 py-1 rounded-md flex items-center gap-1 border border-purple-100">
            <Bot size={12} />
            Requirements Collector Agent
            <button className="hover:text-purple-900 ml-1"><X size={12}/></button>
          </div>
        </div>

        <div className="flex items-end gap-2 px-2 pb-1">
          <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full mb-1">
            <Paperclip size={20} />
          </button>
          
          <textarea
            className="flex-1 max-h-32 bg-transparent border-none focus:ring-0 resize-none py-3 text-sm placeholder:text-gray-400 text-gray-700 outline-none"
            placeholder="Type your response..."
            rows={1}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown} // Trigger send on Enter
          />

          <div className="flex items-center gap-2 mb-1">
             <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full">
                <Mic size={20} />
             </button>
             <button 
               onClick={handleSend} // Trigger send on Click
               className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
             >
                <Send size={18} />
             </button>
          </div>
        </div>
      </div>
    </div>
  );
}