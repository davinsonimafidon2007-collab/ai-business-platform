import { describe, it, expect, vi, beforeEach } from "vitest";
import { signInWithGoogle, signOutOfGoogle, initGoogleAuth } from "@/app/services/google-auth";
import { useAuthStore } from "@/app/store/auth-store";
import { secureStorage } from "@/app/services/storage";
import type { User } from "@/app/types/auth";

vi.mock("@capacitor/core", () => ({
  Capacitor: { getPlatform: vi.fn(), isNativePlatform: vi.fn() },
}));
vi.mock("firebase/auth", () => ({
  signInWithPopup: vi.fn(),
  signInWithCredential: vi.fn(),
  GoogleAuthProvider: { credential: vi.fn() },
  signOut: vi.fn(),
}));
vi.mock("@/app/config/firebase", () => ({
  auth: {},
  googleProvider: { providerId: "google.com" },
  firebaseConfigured: true,
}));
vi.mock("@/app/services/api/client", () => ({
  api: { post: vi.fn(), get: vi.fn() },
}));

import { Capacitor } from "@capacitor/core";
import { signInWithPopup, signOut } from "firebase/auth";
import { api } from "@/app/services/api/client";

const user: User = {
  id: "u1",
  email: "test@example.com",
  full_name: "Test User",
  is_verified: true,
  role: "user",
  created_at: "2024-01-01T00:00:00Z",
};

describe("google-auth (web)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (Capacitor.getPlatform as any).mockReturnValue("web");
    (Capacitor.isNativePlatform as any).mockReturnValue(false);
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: true,
    });
    window.localStorage.clear();
  });

  it("initGoogleAuth is a no-op on the web platform", () => {
    expect(() => initGoogleAuth()).not.toThrow();
  });

  it("signInWithGoogle exchanges the ID token and persists the session", async () => {
    (signInWithPopup as any).mockResolvedValue({
      user: { getIdToken: () => Promise.resolve("id-token") },
    });
    (api.post as any).mockResolvedValue({
      data: { access_token: "at", refresh_token: "rt", token_type: "bearer" },
    });
    (api.get as any).mockResolvedValue({ data: user });

    await signInWithGoogle();

    expect(signInWithPopup).toHaveBeenCalled();
    expect(api.post).toHaveBeenCalledWith("/auth/google", {
      id_token: "id-token",
    });
    expect(api.get).toHaveBeenCalledWith("/auth/me");

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.user?.email).toBe("test@example.com");
    // El storage seguro web persiste bajo SECURE_PREFIX con encode.
    expect(await secureStorage.get("access_token")).toBe("at");
    expect(await secureStorage.get("refresh_token")).toBe("rt");
  });

  it("signInWithGoogle throws when no ID token is returned", async () => {
    (signInWithPopup as any).mockResolvedValue({
      user: { getIdToken: () => Promise.resolve(null) },
    });

    await expect(signInWithGoogle()).rejects.toThrow(
      "No se recibió el token de Google"
    );
  });

  it("signOutOfGoogle signs out of Firebase on web", async () => {
    (signOut as any).mockResolvedValue(undefined);

    await signOutOfGoogle();

    expect(signOut).toHaveBeenCalled();
  });
});
