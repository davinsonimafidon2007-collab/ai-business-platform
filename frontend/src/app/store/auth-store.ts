import { create } from "zustand";
import { User } from "@/app/types/auth";
import { isAuthDisabled, LOCAL_USER } from "@/app/config/app-mode";

// Claves de localStorage. Centralizadas aquí para que login/register/google/auth
// client compartan el mismo contrato y no haya strings sueltos.
export const TOKEN_KEYS = {
  accessToken: "access_token",
  refreshToken: "refresh_token",
  user: "user",
} as const;

export interface SetSessionParams {
  accessToken: string;
  refreshToken: string;
  user: User;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  setSession: (params: SetSessionParams) => void;
  logout: () => void;
  initialize: () => void;
}

// Guarda / lee de localStorage solo en el cliente (SSR-safe) y mantiene
// compatibilidad con Capacitor WebView (localStorage disponible ahí).
const storage = {
  get(key: string): string | null {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(key);
  },
  set(key: string, value: string): void {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(key, value);
  },
  remove(key: string): void {
    if (typeof window === "undefined") return;
    window.localStorage.removeItem(key);
  },
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  setUser: (user) =>
    set({ user, isAuthenticated: !!user, isLoading: false }),
  setLoading: (isLoading) => set({ isLoading }),
  // Path canónico para persistir una sesión: login, register y Google.
  // Centraliza la escritura en localStorage y el update del store,
  // evitando que cada flujo copie la persistencia a mano.
  setSession: ({ accessToken, refreshToken, user }) => {
    storage.set(TOKEN_KEYS.accessToken, accessToken);
    storage.set(TOKEN_KEYS.refreshToken, refreshToken);
    storage.set(TOKEN_KEYS.user, JSON.stringify(user));
    set({ user, isAuthenticated: true, isLoading: false });
  },
  logout: () => {
    storage.remove(TOKEN_KEYS.accessToken);
    storage.remove(TOKEN_KEYS.refreshToken);
    storage.remove(TOKEN_KEYS.user);
    set({ user: null, isAuthenticated: false, isLoading: false });
  },
  initialize: () => {
    // Auth desactivada (uso personal): autentica directamente al usuario local
    // sin token → sin redirección a login y con sesión "activa" para la UI.
    if (isAuthDisabled()) {
      set({
        user: LOCAL_USER,
        isAuthenticated: true,
        isLoading: false,
      });
      return;
    }
    try {
      const token = storage.get(TOKEN_KEYS.accessToken);
      const userStr = storage.get(TOKEN_KEYS.user);
      // Protección básica: no aceptar tokens vacíos o corruptos
      if (token && token.trim().length > 0 && userStr) {
        const user = JSON.parse(userStr) as User;
        set({ user, isAuthenticated: true, isLoading: false });
      } else {
        set({ isLoading: false });
      }
    } catch {
      set({ isLoading: false });
    }
    // TODO(FE-001): opcional — validar expiración del access token (payload `exp`)
    // y, si parece expirado, intentar refresh una vez o marcar no autenticado.
    // No implementado aquí para mantener el cambio mínimo y testeable.
  },
}));
