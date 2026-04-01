import { create } from "zustand";

/** Payload from GET /llm-runtime or POST save/verify ``runtime`` (enriched). */
export type LlmRuntimePayload = {
  model?: string;
  source?: string;
  mode?: string;
  saved_model?: string;
  saved_mode?: string;
  saved_verified?: boolean;
  has_custom_key?: boolean;
};

/** Shared UI: open LLM settings from project console chip; refresh console model chip after settings close. */
export const useLlmUiStore = create<{
  llmModalOpen: boolean;
  setLlmModalOpen: (open: boolean) => void;
  llmRuntimeRefreshNonce: number;
  bumpLlmRuntimeRefresh: () => void;
  llmRuntimePayload: LlmRuntimePayload | null;
  setLlmRuntimePayload: (p: LlmRuntimePayload | null) => void;
}>((set) => ({
  llmModalOpen: false,
  setLlmModalOpen: (open) => set({ llmModalOpen: open }),
  llmRuntimeRefreshNonce: 0,
  bumpLlmRuntimeRefresh: () =>
    set((s) => ({ llmRuntimeRefreshNonce: s.llmRuntimeRefreshNonce + 1 })),
  llmRuntimePayload: null,
  setLlmRuntimePayload: (p) => set({ llmRuntimePayload: p }),
}));
