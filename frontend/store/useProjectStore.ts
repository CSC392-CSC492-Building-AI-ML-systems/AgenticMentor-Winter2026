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
  isLoading: boolean

  setProjectId: (id: string) => void
  setProjectName: (name: string) => void
  addMessage: (msg: any) => void
  setRequirements: (data: any) => void
  setArchitecture: (data: any) => void
  setRoadmap: (data: any) => void
  setMockups: (data: any[]) => void
  setCurrentPhase: (phase: string) => void
  setAgentResults: (results: AgentResult[]) => void
  setAvailableAgents: (agents: AvailableAgent[]) => void
  setIsLoading: (loading: boolean) => void
  /** Apply a full state snapshot from the API response */
  applyStateSnapshot: (snapshot: any) => void
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projectId: null,
  projectName: null,
  messages: [],
  requirements: null,
  architecture: null,
  roadmap: null,
  mockups: [],
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
  setIsLoading: (loading) => set({ isLoading: loading }),

  applyStateSnapshot: (snapshot) => {
    if (!snapshot) return
    set({
      currentPhase: snapshot.current_phase ?? "initialization",
      requirements: snapshot.requirements ?? null,
      architecture: snapshot.architecture ?? null,
      roadmap: snapshot.roadmap ?? null,
      mockups: snapshot.mockups ?? [],
    })
  },
}))
