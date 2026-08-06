import { describe, it, expect, beforeEach } from "vitest";
import { useAuthStore, TOKEN_KEYS } from "@/app/store/auth-store";
import type { User } from "@/app/types/auth";

const user: User = {
  id: "user-1",
  email: "user@example.com",
  full_name: "Test User",
  is_verified: true,
  role: "user",
  created_at: "2024-01-01T00:00:00Z",
};

describe("auth-store", () => {
  beforeEach(() => {
    window.localStorage.clear();
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: true,
    });
  });

  it("setSession persiste tokens + user y autentica", () => {
    useAuthStore
      .getState()
      .setSession({ accessToken: "at", refreshToken: "rt", user });

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.isLoading).toBe(false);
    expect(state.user?.email).toBe("user@example.com");
    expect(window.localStorage.getItem(TOKEN_KEYS.accessToken)).toBe("at");
    expect(window.localStorage.getItem(TOKEN_KEYS.refreshToken)).toBe("rt");
    expect(window.localStorage.getItem(TOKEN_KEYS.user)).toBe(
      JSON.stringify(user)
    );
  });

  it("initialize hidrata desde localStorage cuando hay token + user", () => {
    window.localStorage.setItem(TOKEN_KEYS.accessToken, "at");
    window.localStorage.setItem(TOKEN_KEYS.user, JSON.stringify(user));

    useAuthStore.getState().initialize();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.isLoading).toBe(false);
    expect(state.user?.email).toBe("user@example.com");
  });

  it("initialize marca no autenticado y deja de cargar sin token", () => {
    useAuthStore.getState().initialize();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isLoading).toBe(false);
  });

  it("initialize no rompe con user JSON inválido", () => {
    window.localStorage.setItem(TOKEN_KEYS.accessToken, "at");
    window.localStorage.setItem(TOKEN_KEYS.user, "{invalid json");

    useAuthStore.getState().initialize();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isLoading).toBe(false);
  });

  it("logout limpia estado y localStorage", () => {
    useAuthStore
      .getState()
      .setSession({ accessToken: "at", refreshToken: "rt", user });

    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
    expect(state.isLoading).toBe(false);
    expect(window.localStorage.getItem(TOKEN_KEYS.accessToken)).toBeNull();
    expect(window.localStorage.getItem(TOKEN_KEYS.refreshToken)).toBeNull();
    expect(window.localStorage.getItem(TOKEN_KEYS.user)).toBeNull();
  });
});
