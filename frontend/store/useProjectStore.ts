import { create } from "zustand"

export interface AgentResult {
  agent_id: string
  agent_name: string
  status: string
  content: string
  state_delta_keys: string[]
  error?: string | null
}

export interface AvailableAgent {
  agent_id: string
  agent_name: string
  description: string
  is_available: boolean
  is_phase_compatible: boolean
  unmet_requires: string[]
  blocked_by: string[]
  interaction_mode: string
  expensive: boolean
}

interface ProjectStore {
  projectId: string | null
  projectName: string | null
  messages: any[]
  requirements: any | null
  architecture: any | null
  roadmap: any | null
  mockups: any[]
  currentPhase: string
  agentResults: AgentResult[]
  availableAgents: AvailableAgent[]
  exportArtifacts: any | null
  isLoading: boolean
  nextRecommendedAgentId: string | null
  activeTab: string

  setProjectId: (id: string) => void
  setActiveTab: (tab: string) => void
  setProjectName: (name: string) => void
  addMessage: (msg: any) => void
  setRequirements: (data: any) => void
  setArchitecture: (data: any) => void
  setRoadmap: (data: any) => void
  setMockups: (data: any[]) => void
  setCurrentPhase: (phase: string) => void
  setAgentResults: (results: AgentResult[]) => void
  setAvailableAgents: (agents: AvailableAgent[]) => void
  setMessages: (msgs: any[]) => void
  setIsLoading: (loading: boolean) => void
  setNextRecommendedAgentId: (id: string | null) => void
  resetProject: () => void
  /** Apply a full state snapshot from the API response */
  applyStateSnapshot: (snapshot: any, options?: { restoreHistory?: boolean }) => void
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projectId: null,
  projectName: null,
  messages: [],
  requirements: null,
  architecture: null,
  roadmap: null,
  mockups: [],
  exportArtifacts: null,
  nextRecommendedAgentId: null,
  activeTab: "req",
  currentPhase: "initialization",
  agentResults: [],
  availableAgents: [],
  isLoading: false,

  setProjectId: (id) => set({ projectId: id }),
  setProjectName: (name) => set({ projectName: name }),
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  setRequirements: (data) => set({ requirements: data }),
  setArchitecture: (data) => set({ architecture: data }),
  setRoadmap: (data) => set({ roadmap: data }),
  setMockups: (data) => set({ mockups: data }),
  setCurrentPhase: (phase) => set({ currentPhase: phase }),
  setAgentResults: (results) => set({ agentResults: results }),
  setAvailableAgents: (agents) => set({ availableAgents: agents }),
  setMessages: (msgs) => set({ messages: msgs }),
  setIsLoading: (loading) => set({ isLoading: loading }),
  setNextRecommendedAgentId: (id) => set({ nextRecommendedAgentId: id }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  resetProject: () => set({
    messages: [],
    requirements: null,
    architecture: null,
    roadmap: null,
    mockups: [],
    currentPhase: "initialization",
    agentResults: [],
    availableAgents: [],
    nextRecommendedAgentId: null,
  }),

  applyStateSnapshot: (snapshot, options = {}) => {
    if (!snapshot) return
    const reqs = snapshot.requirements
    const updates: Partial<ProjectStore> = {
      currentPhase: snapshot.current_phase ?? "initialization",
      requirements: reqs ?? null,
      architecture: snapshot.architecture ?? null,
      roadmap: snapshot.roadmap ?? null,
      mockups: snapshot.mockups ?? [],
      exportArtifacts: snapshot.export_artifacts ?? null,
      nextRecommendedAgentId: snapshot.next_recommended_agent_id ?? null,
      ...(snapshot.project_name ? { projectName: snapshot.project_name } : {}),
    }
    // Only restore conversation history on explicit initial load, not during live chat
    if (options.restoreHistory && snapshot.conversation_history?.length) {
      const ts = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
      updates.messages = snapshot.conversation_history.map((entry: any, i: number) => ({
        id: `history-${i}`,
        role: entry.role === "user" ? "user" : "agent",
        agentName: entry.role === "user" ? undefined : "Orchestrator",
        content: entry.content ?? "",
        timestamp: entry.timestamp ?? ts,
      }))
    }
    set(updates)
  },
}))
