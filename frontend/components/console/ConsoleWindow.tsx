"use client";
import { useState, useRef, useEffect } from "react"; // useState kept for isAgentTyping
import ConsoleMessage from "./ConsoleMessage";
import ConsoleInput from "./ConsoleInput";
import { useProjectStore } from "@/store/useProjectStore";
import { useAuthStore } from "@/store/useAuthStore";
import { useLlmUiStore, type LlmRuntimePayload } from "@/store/useLlmUiStore";
import { fetchWithAuth } from "@/lib/api";

const AGENT_ID_MAP: Record<string, string> = {
  requirements: "requirements_collector",
  project_architect: "project_architect",
  execution_planner: "execution_planner",
  mockup_rendering: "mockup_agent",
  exporter: "exporter",
};

const AGENT_TAB_MAP: Record<string, string> = {
  requirements_collector: "req",
  project_architect: "arch",
  execution_planner: "exec",
  mockup_agent: "mock",
};

function formatLlmChipLine(data: LlmRuntimePayload): string {
  const effModel = String(data.model ?? "").trim();
  const src = String(data.source ?? "");
  const savedMode = data.saved_mode != null ? String(data.saved_mode) : "";
  const savedModel = data.saved_model != null ? String(data.saved_model).trim() : "";
  const usingCustom = src === "custom";
  const modelStr = usingCustom
    ? effModel
    : savedMode === "custom" && savedModel
      ? savedModel
      : effModel;
  const savedVerified = Boolean(data.saved_verified);
  const hasKey = Boolean(data.has_custom_key);
  const sourceLabel =
    src === "custom"
      ? "your key"
      : savedMode === "custom" && savedVerified && !hasKey
        ? "add key"
        : savedMode === "custom"
          ? "verify key"
          : "app key";
  if (!modelStr) return "LLM · …";
  return `${modelStr} · ${sourceLabel}`;
}

export default function ConsoleWindow() {
  const [isAgentTyping, setIsAgentTyping] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { projectId, messages, addMessage, applyStateSnapshot, setAgentResults, setAvailableAgents, availableAgents, nextRecommendedAgentId, setNextRecommendedAgentId, setActiveTab } = useProjectStore();

  const { idToken } = useAuthStore();
  const llmRuntimeRefreshNonce = useLlmUiStore((s) => s.llmRuntimeRefreshNonce);
  const setLlmModalOpen = useLlmUiStore((s) => s.setLlmModalOpen);
  const llmRuntimePayload = useLlmUiStore((s) => s.llmRuntimePayload);
  const setLlmRuntimePayload = useLlmUiStore((s) => s.setLlmRuntimePayload);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAgentTyping]);

  useEffect(() => {
    if (!projectId || !idToken) {
      setLlmRuntimePayload(null);
      return;
    }
    let cancelled = false;
    fetchWithAuth(`/projects/${projectId}/llm-runtime?r=${llmRuntimeRefreshNonce}`, { token: idToken })
      .then(async (res) => {
        const data = (await res.json()) as LlmRuntimePayload;
        if (!res.ok) return;
        if (!cancelled && data && typeof data === "object") setLlmRuntimePayload(data);
      })
      .catch(() => {
        if (!cancelled) setLlmRuntimePayload(null);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, idToken, llmRuntimeRefreshNonce, setLlmRuntimePayload]);

  const handleSendMessage = async (text: string, agent: any, switchTab = false) => {
    const ts = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

    addMessage({
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: ts(),
    });
    setIsAgentTyping(agent.name);

    if (!projectId || !idToken) {
      addMessage({
        id: (Date.now() + 1).toString(),
        role: "agent",
        agentName: "System",
        avatarColor: "gray",
        content: "No active project. Please open a project first.",
        timestamp: ts(),
      });
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

      if (switchTab) {
        const completedAgentId = (data.agent_results ?? [])[0]?.agent_id;
        const tab = AGENT_TAB_MAP[completedAgentId];
        if (tab) setActiveTab(tab);
      }

      const rt = data.llm_runtime as LlmRuntimePayload | undefined;
      if (rt && typeof rt === "object") {
        useLlmUiStore.getState().setLlmRuntimePayload(rt);
      }

      const subLines: string[] = (data.agent_results ?? []).map((ar: any) => {
        const icon = ar.status === "success" ? "✓" : "✗";
        const detail = ar.status !== "success" && ar.error ? ` (${ar.error})` : "";
        return `${icon} [${ar.agent_name}] ${ar.status}${detail}`;
      });

      addMessage({
          id: (Date.now() + 1).toString(),
          role: "agent",
          agentName: agent.name,
          avatarColor: agent.color,
          content: data.message || "Done.",
          subLines,
          timestamp: ts(),
        });
    } catch (err: any) {
      addMessage({
        id: (Date.now() + 2).toString(),
        role: "agent",
        agentName: "System",
        avatarColor: "red",
        content: `Error: ${err.message ?? "Unknown error"}`,
        timestamp: ts(),
      });
    } finally {
      setIsAgentTyping(null);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-black font-mono transition-colors">

      <div className="h-8 border-b border-gray-300 dark:border-[#444] flex items-center justify-between gap-2 px-3 sm:px-4 bg-gray-50 dark:bg-[#050505] shrink-0 transition-colors min-w-0">
        <span className="text-[10px] font-bold text-black dark:text-white tracking-widest uppercase shrink-0">
          System_Console
        </span>
        <button
          type="button"
          onClick={() => setLlmModalOpen(true)}
          className="min-w-0 flex-1 text-right text-[9px] font-bold uppercase tracking-widest text-gray-600 dark:text-gray-400 hover:text-black dark:hover:text-white underline-offset-2 hover:underline truncate"
          title="Open LLM settings"
        >
          {llmRuntimePayload ? formatLlmChipLine(llmRuntimePayload) : "LLM · …"}
        </button>
        <div className="flex gap-2 shrink-0">
          <div className="w-2 h-2 rounded-full bg-gray-300 dark:bg-[#555]"></div>
          <div className="w-2 h-2 rounded-full bg-black dark:bg-white"></div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 bg-white dark:bg-black transition-colors">
        {messages.length === 0 && (
          <div className="text-xs text-gray-500 font-bold uppercase tracking-widest mb-6">
            -- CONSOLE INITIALIZED. WAITING FOR OPERATOR INPUT --
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id}>
            <ConsoleMessage message={msg} />
            {msg.subLines?.map((line: string, i: number) => (
              <div key={i} className="font-mono text-xs text-gray-500 dark:text-gray-400 pl-3 mb-0.5 whitespace-pre-wrap">
                {line}
              </div>
            ))}
          </div>
        ))}

        {isAgentTyping && (
          <div className="font-mono text-xs mb-4 px-2 py-1.5">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-bold uppercase tracking-widest text-[11px] text-black dark:text-white">
                Orchestrator
              </span>
              <span className="text-[9px] text-gray-400 dark:text-gray-500">
                {new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
            </div>
            <div className="text-[11px] text-gray-500 dark:text-gray-400 pl-1 animate-pulse">
              Estimated response: 15–45 seconds █
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {(() => {
        if (!nextRecommendedAgentId) return null;
        const agent = availableAgents.find((a) => a.agent_id === nextRecommendedAgentId);
        if (!agent || !agent.is_available) return null;
        const label = agent.agent_name.replace(/_/g, " ");
        return (
          <div className="px-6 pb-2 shrink-0">
            <button
              onClick={() => {
                setNextRecommendedAgentId(null);
                handleSendMessage(`Run the ${agent.agent_name}`, { id: "auto", name: "Orchestrator", color: "white" }, true);
              }}
              disabled={!!isAgentTyping}
              className="flex items-center gap-2 px-3 py-1.5 border border-gray-300 dark:border-[#444] text-[9px] font-bold uppercase tracking-widest text-gray-600 dark:text-gray-400 hover:border-black hover:text-black dark:hover:border-white dark:hover:text-white transition-colors disabled:opacity-40"
            >
              <span className="text-[8px] text-gray-400">▶</span>
              Next: {label}
            </button>
          </div>
        );
      })()}

      <ConsoleInput onSend={handleSendMessage} />
    </div>
  );
}