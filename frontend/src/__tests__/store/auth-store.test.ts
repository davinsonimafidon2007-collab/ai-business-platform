import { describe, it, expect, beforeEach } from "vitest";
import { useAuthStore, TOKEN_KEYS, getTokenExpiry, decodeJwtPayload } from "@/app/store/auth-store";
import { secureStorage, SECURE_PREFIX } from "@/app/services/storage";
import type { User } from "@/app/types/auth";

const user: User = {
  id: "user-1",
  email: "user@example.com",
  full_name: "Test User",
  is_verified: true,
  role: "user",
  created_at: "2024-01-01T00:00:00Z",
};

// JWT de prueba: header.payload.signature (payload base64url, sin verificar).
const b64url = (obj: object) =>
  btoa(JSON.stringify(obj)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const makeJwt = (payload: object) => `header.${b64url(payload)}.signature`;

describe("auth-store", () => {
  beforeEach(async () => {
    await secureStorage.clear();
    window.localStorage.clear();
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: true,
    });
  });

  it("setSession persiste tokens + user y autentica", async () => {
    await useAuthStore
      .getState()
      .setSession({ accessToken: "at", refreshToken: "rt", user });

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.isLoading).toBe(false);
    expect(state.user?.email).toBe("user@example.com");
    expect(await secureStorage.get(TOKEN_KEYS.accessToken)).toBe("at");
    expect(await secureStorage.get(TOKEN_KEYS.refreshToken)).toBe("rt");
    expect(await secureStorage.get(TOKEN_KEYS.user)).toBe(
      JSON.stringify(user)
    );
  });

  it("initialize hidrata desde localStorage cuando hay token + user", async () => {
    await secureStorage.set(TOKEN_KEYS.accessToken, "at");
    await secureStorage.set(TOKEN_KEYS.user, JSON.stringify(user));

    await useAuthStore.getState().initialize();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.isLoading).toBe(false);
    expect(state.user?.email).toBe("user@example.com");
  });

  it("initialize marca no autenticado y deja de cargar sin token", async () => {
    await useAuthStore.getState().initialize();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isLoading).toBe(false);
  });

  it("initialize no rompe con user JSON inválido", async () => {
    await secureStorage.set(TOKEN_KEYS.accessToken, "at");
    await secureStorage.set(TOKEN_KEYS.user, "{invalid json");

    await useAuthStore.getState().initialize();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isLoading).toBe(false);
  });

  it("logout limpia estado y localStorage", async () => {
    await useAuthStore
      .getState()
      .setSession({ accessToken: "at", refreshToken: "rt", user });

    await useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.user).toBeNull();
    expect(state.isLoading).toBe(false);
    expect(await secureStorage.get(TOKEN_KEYS.accessToken)).toBeNull();
    expect(await secureStorage.get(TOKEN_KEYS.refreshToken)).toBeNull();
    expect(await secureStorage.get(TOKEN_KEYS.user)).toBeNull();
  });

  it("initialize no hidrata sesión con access token expirado y limpia storage", async () => {
    const expiredToken = makeJwt({ exp: Math.floor(Date.now() / 1000) - 1000 });
    await secureStorage.set(TOKEN_KEYS.accessToken, expiredToken);
    await secureStorage.set(TOKEN_KEYS.refreshToken, "rt");
    await secureStorage.set(TOKEN_KEYS.user, JSON.stringify(user));

    await useAuthStore.getState().initialize();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isLoading).toBe(false);
    expect(await secureStorage.get(TOKEN_KEYS.accessToken)).toBeNull();
    expect(await secureStorage.get(TOKEN_KEYS.refreshToken)).toBeNull();
    expect(await secureStorage.get(TOKEN_KEYS.user)).toBeNull();
  });

  it("initialize hidrata sesión cuando el token no está expirado", async () => {
    const validToken = makeJwt({ exp: Math.floor(Date.now() / 1000) + 3600 });
    await secureStorage.set(TOKEN_KEYS.accessToken, validToken);
    await secureStorage.set(TOKEN_KEYS.user, JSON.stringify(user));

    await useAuthStore.getState().initialize();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.email).toBe("user@example.com");
  });

  it("getTokenExpiry devuelve null para tokens no JWT o sin exp", () => {
    expect(getTokenExpiry("at")).toBeNull();
    expect(getTokenExpiry(makeJwt({ sub: "user-1" }))).toBeNull();
    expect(getTokenExpiry("a.b")).toBeNull();
  });

  it("decodeJwtPayload no rompe con payload corrupto", () => {
    expect(decodeJwtPayload("a.b.c")).toBeNull();
    expect(decodeJwtPayload("header.%%%.sig")).toBeNull();
    expect(decodeJwtPayload(makeJwt({ exp: 123 }))).toEqual({ exp: 123 });
  });

  it("setUser actualiza usuario y autenticación", () => {
    useAuthStore.getState().setUser(user);

    const state = useAuthStore.getState();
    expect(state.user?.email).toBe("user@example.com");
    expect(state.isAuthenticated).toBe(true);
    expect(state.isLoading).toBe(false);
  });

  it("setUser(null) desautentica", () => {
    useAuthStore.getState().setUser(user);
    useAuthStore.getState().setUser(null);

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isLoading).toBe(false);
  });

  it("setLoading actualiza solo el flag de carga", () => {
    useAuthStore.getState().setLoading(true);
    expect(useAuthStore.getState().isLoading).toBe(true);
    useAuthStore.getState().setLoading(false);
    expect(useAuthStore.getState().isLoading).toBe(false);
  });

  it("initialize autentica al usuario local cuando la auth está desactivada", () => {
    process.env.NEXT_PUBLIC_AUTH_DISABLED = "true";
    try {
      useAuthStore.getState().initialize();
      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.user?.email).toBe("local@example.com");
    } finally {
      delete process.env.NEXT_PUBLIC_AUTH_DISABLED;
    }
  });
});
