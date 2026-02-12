import { create } from "zustand"

interface ProjectState {
  projectId: string | null
  messages: any[]
  requirements: any | null
  architecture: any | null
  executionPlan: any | null

  setProjectId: (id: string) => void
  addMessage: (msg: any) => void
  setRequirements: (data: any) => void
  setArchitecture: (data: any) => void
  setExecutionPlan: (data: any) => void
}

export const useProjectStore = create<ProjectState>((set) => ({
  projectId: null,
  messages: [],
  requirements: null,
  architecture: null,
  executionPlan: null,

  setProjectId: (id) => set({ projectId: id }),
  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),
  setRequirements: (data) => set({ requirements: data }),
  setArchitecture: (data) => set({ architecture: data }),
  setExecutionPlan: (data) => set({ executionPlan: data }),
}))
