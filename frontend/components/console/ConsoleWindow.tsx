"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import ConsoleMessage from "./ConsoleMessage";
import ConsoleInput from "./ConsoleInput";
import { useProjectStore } from "@/store/useProjectStore";
import { useAuthStore } from "@/store/useAuthStore";
import { fetchWithAuth } from "@/lib/api";

const AGENT_ID_MAP: Record<string, string> = {
  requirements: "requirements_collector",
  project_architect: "project_architect",
  execution_planner: "execution_planner",
  mockup_rendering: "mockup_agent",
  exporter: "exporter",
};

export default function ConsoleWindow() {
  const [messages, setMessages] = useState<any[]>([]);
  const [isAgentTyping, setIsAgentTyping] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(350);
  const isDragging = useRef(false);

  const { projectId, applyStateSnapshot, setAgentResults, setAvailableAgents } = useProjectStore();
  const { idToken } = useAuthStore();

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAgentTyping]);

  const startResizing = (e: React.MouseEvent) => {
    isDragging.current = true;
    document.addEventListener("mousemove", resize);
    document.addEventListener("mouseup", stopResizing);
    document.body.style.cursor = "ns-resize";
    document.body.style.userSelect = "none";
  };

  const resize = useCallback((e: MouseEvent) => {
    if (isDragging.current) {
      const newHeight = window.innerHeight - e.clientY;
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

  const handleSendMessage = async (text: string, agent: any) => {
    const ts = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

    setMessages((prev) => [...prev, {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: ts(),
    }]);
    setIsAgentTyping(agent.name);

    if (!projectId || !idToken) {
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "agent",
        agentName: "System",
        avatarColor: "gray",
        content: "No active project. Please open a project first.",
        timestamp: ts(),
      }]);
      setIsAgentTyping(null);
      return;
    }

    const isAuto = agent.id === "auto";
    const backendAgentId = isAuto ? null : (AGENT_ID_MAP[agent.id] ?? agent.id);

    try {
      const res = await fetchWithAuth(`/projects/${projectId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        token: idToken,
        body: JSON.stringify({
          message: text,
          agent_selection_mode: isAuto ? "auto" : "manual",
          selected_agent_id: backendAgentId,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }

      if (data.state) applyStateSnapshot(data.state);
      if (data.available_agents) setAvailableAgents(data.available_agents);
      if (data.agent_results) setAgentResults(data.agent_results);

      // Build per-agent status sub-lines for the console
      const subLines: string[] = (data.agent_results ?? []).map((ar: any) => {
        const icon = ar.status === "success" ? "✓" : "✗";
        const detail = ar.status !== "success" && ar.error ? ` (${ar.error})` : "";
        return `${icon} [${ar.agent_name}] ${ar.status}${detail}`;
      });

      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "agent",
        agentName: agent.name,
        avatarColor: agent.color,
        content: data.message || "Done.",
        subLines,
        timestamp: ts(),
      }]);
    } catch (err: any) {
      setMessages((prev) => [...prev, {
        id: (Date.now() + 2).toString(),
        role: "agent",
        agentName: "System",
        avatarColor: "red",
        content: `Error: ${err.message ?? "Unknown error"}`,
        timestamp: ts(),
      }]);
    } finally {
      setIsAgentTyping(null);
    }
  };

  return (
    <div style={{ height: `${height}px` }} className="flex flex-col bg-white dark:bg-black font-mono relative flex-shrink-0 w-full transition-colors border-t border-gray-300 dark:border-[#444]">
      
      <div 
        onMouseDown={startResizing}
        className="absolute top-0 left-0 w-full h-1.5 bg-gray-300 dark:bg-[#444] hover:bg-black dark:hover:bg-white cursor-ns-resize transition-colors z-50 flex-shrink-0"
        title="Drag to resize console"
      />

      <div className="h-8 border-b border-gray-300 dark:border-[#444] flex items-center justify-between px-4 bg-gray-50 dark:bg-[#050505] mt-1.5 transition-colors">
        <span className="text-[10px] font-bold text-black dark:text-white tracking-widest uppercase">System_Console</span>
        <div className="flex gap-2">
           <div className="w-2 h-2 rounded-full bg-gray-300 dark:bg-[#555]"></div>
           <div className="w-2 h-2 rounded-full bg-black dark:bg-white"></div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 bg-white dark:bg-black transition-colors">
        {messages.length === 0 && (
          <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-6">
            -- CONSOLE INITIALIZED. WAITING FOR OPERATOR INPUT --
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id}>
            <ConsoleMessage message={msg} />
            {msg.subLines?.map((line: string, i: number) => (
              <div key={i} className="font-mono text-[10px] text-gray-500 dark:text-gray-400 ml-16 mb-0.5 whitespace-pre-wrap">
                {line}
              </div>
            ))}
          </div>
        ))}
        
        {isAgentTyping && (
          <div className="font-mono text-xs sm:text-sm mb-3 flex gap-4 text-gray-800 dark:text-gray-200 mt-4">
            <span className="text-gray-400 dark:text-gray-500">[{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span>
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