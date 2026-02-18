"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import ConsoleMessage from "./ConsoleMessage";
import ConsoleInput from "./ConsoleInput";

export default function ConsoleWindow() {
  const [messages, setMessages] = useState<any[]>([]); 
  const [isAgentTyping, setIsAgentTyping] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // Resizing State
  const [height, setHeight] = useState(350); // Default starting height (pixels)
  const isDragging = useRef(false);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAgentTyping]);

  // --- RESIZE LOGIC ---
  const startResizing = (e: React.MouseEvent) => {
    isDragging.current = true;
    document.addEventListener("mousemove", resize);
    document.addEventListener("mouseup", stopResizing);
    document.body.style.cursor = "ns-resize"; // Prevent cursor flickering while dragging
    document.body.style.userSelect = "none";  // Prevent text highlighting while dragging
  };

  const resize = useCallback((e: MouseEvent) => {
    if (isDragging.current) {
      // Calculate new height: Viewport height minus the mouse's Y position
      const newHeight = window.innerHeight - e.clientY;
      // Constrain it so it doesn't get too small or crush the top panels entirely
      const constrainedHeight = Math.max(100, Math.min(newHeight, window.innerHeight * 0.8));
      setHeight(constrainedHeight);
    }
  }, []);

  const stopResizing = useCallback(() => {
    isDragging.current = false;
    document.removeEventListener("mousemove", resize);
    document.removeEventListener("mouseup", stopResizing);
    document.body.style.cursor = "default";
    document.body.style.userSelect = "auto";
  }, [resize]);
  // --------------------

  const handleSendMessage = (text: string, agent: any) => {
    const userMsg = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsAgentTyping(agent.name);

    setTimeout(() => {
      const aiMsg = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        agentName: agent.name,
        avatarColor: agent.color,
        content: `Acknowledge request: "${text}". Processing matrix parameters and updating system state.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      };
      setMessages((prev) => [...prev, aiMsg]);
      setIsAgentTyping(null);
    }, 1200);
  };

  return (
    // Replaced static height with dynamic inline style
    <div style={{ height: `${height}px` }} className="flex flex-col bg-black font-mono relative flex-shrink-0 w-full">
      
      {/* The Drag Handle (Also acts as the top border) */}
      <div 
        onMouseDown={startResizing}
        className="w-full h-1.5 bg-[#444] hover:bg-white cursor-ns-resize transition-colors z-50 flex-shrink-0"
        title="Drag to resize console"
      />

      <div className="h-8 border-b border-[#444] flex items-center justify-between px-4 bg-[#050505]">
        <span className="text-[10px] font-bold text-white tracking-widest uppercase">System_Console</span>
        <div className="flex gap-2">
           <div className="w-2 h-2 rounded-full bg-[#555]"></div>
           <div className="w-2 h-2 rounded-full bg-white"></div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 bg-black">
        {messages.length === 0 && (
          <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-6">
            -- CONSOLE INITIALIZED. WAITING FOR OPERATOR INPUT --
          </div>
        )}

        {messages.map((msg) => <ConsoleMessage key={msg.id} message={msg} />)}
        
        {isAgentTyping && (
          <div className="font-mono text-xs sm:text-sm mb-3 flex gap-4 text-gray-200 mt-4">
            <span className="text-gray-400">[{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span>
            <span className="font-bold uppercase w-24 text-right">SYS:{isAgentTyping.split(" ")[0]} &gt;</span>
            <span className="animate-pulse">Processing request... █</span>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      <ConsoleInput onSend={handleSendMessage} />
    </div>
  );
}