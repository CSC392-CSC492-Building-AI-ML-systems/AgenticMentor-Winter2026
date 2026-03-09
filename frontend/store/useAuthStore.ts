import { create } from "zustand";
import { persist } from "zustand/middleware";

const AUTH_STORAGE_KEY = "agentic-mentor-auth";

export interface AuthUser {
  uid: string;
  email: string | null;
  name: string | null;
  picture: string | null;
}

interface AuthState {
  idToken: string | null;
  user: AuthUser | null;
  redirectError: string | null;
  setAuth: (idToken: string, user: AuthUser) => void;
  clearAuth: () => void;
  setRedirectError: (message: string | null) => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      idToken: null,
      user: null,
      redirectError: null,
      setAuth: (idToken, user) => set({ idToken, user, redirectError: null }),
      clearAuth: () => set({ idToken: null, user: null, redirectError: null }),
      setRedirectError: (redirectError) => set({ redirectError }),
      isAuthenticated: () => !!get().idToken,
    }),
    { name: AUTH_STORAGE_KEY, partialize: (s) => ({ idToken: s.idToken, user: s.user }) }
  )
);
