import { create } from "zustand";
import { User } from "@/app/types/auth";
import { isAuthDisabled, LOCAL_USER } from "@/app/config/app-mode";
import { secureStorage } from "@/app/services/storage";

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

// Decodifica el payload (parte 2) de un JWT sin verificar la firma.
// Devuelve null si el token no parece un JWT de 3 segmentos o su payload
// no es JSON válido. Solo se usa para leer `exp`, nunca para validar.
export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const base64url = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64url.padEnd(Math.ceil(base64url.length / 4) * 4, "=");
    const json = atob(padded);
    const payload = JSON.parse(json);
    return typeof payload === "object" && payload !== null ? payload : null;
  } catch {
    return null;
  }
}

// Devuelve la fecha de expiración (`exp`, segundos epoch) del token,
// o null si no es un JWT o no expone `exp`.
export function getTokenExpiry(token: string): number | null {
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") return null;
  return payload.exp;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  setSession: (params: SetSessionParams) => Promise<void>;
  logout: () => Promise<void>;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  setUser: (user) =>
    set({ user, isAuthenticated: !!user, isLoading: false }),
  setLoading: (isLoading) => set({ isLoading }),
  // Path canónico para persistir una sesión: login, register y Google.
  // Centraliza la escritura en el storage seguro (Capacitor Preferences en
  // nativo, localStorage en web) y el update del store, evitando que cada
  // flujo copie la persistencia a mano.
  setSession: async ({ accessToken, refreshToken, user }) => {
    await secureStorage.set(TOKEN_KEYS.accessToken, accessToken);
    await secureStorage.set(TOKEN_KEYS.refreshToken, refreshToken);
    await secureStorage.set(TOKEN_KEYS.user, JSON.stringify(user));
    set({ user, isAuthenticated: true, isLoading: false });
  },
  logout: async () => {
    await secureStorage.remove(TOKEN_KEYS.accessToken);
    await secureStorage.remove(TOKEN_KEYS.refreshToken);
    await secureStorage.remove(TOKEN_KEYS.user);
    set({ user: null, isAuthenticated: false, isLoading: false });
  },
  initialize: async () => {
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
      const token = await secureStorage.get(TOKEN_KEYS.accessToken);
      const userStr = await secureStorage.get(TOKEN_KEYS.user);
      // FE-001: validar la expiración del access token. Si el token expone
      // `exp` y ya venció, no hidratar la sesión: se limpia storage y se
      // marca no autenticado (el API client reintentará refresh si se usa).
      if (token) {
        const exp = getTokenExpiry(token);
        if (exp !== null && exp * 1000 <= Date.now()) {
          await secureStorage.remove(TOKEN_KEYS.accessToken);
          await secureStorage.remove(TOKEN_KEYS.refreshToken);
          await secureStorage.remove(TOKEN_KEYS.user);
          set({ user: null, isAuthenticated: false, isLoading: false });
          return;
        }
      }
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
  },
}));
