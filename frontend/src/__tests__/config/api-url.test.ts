import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock de Capacitor para poder ejercitar la rama Android nativo (10.0.2.2).
const { isNativePlatform, getPlatform } = vi.hoisted(() => {
  const isNativePlatform = vi.fn(() => false);
  const getPlatform = vi.fn(() => "web");
  return { isNativePlatform, getPlatform };
});

vi.mock("@capacitor/core", () => ({
  Capacitor: { isNativePlatform, getPlatform },
}));

import { getApiBaseUrl, setApiBaseUrl } from "@/app/config/api-url";

const OVERRIDE_KEY = "api_base_url";

describe("getApiBaseUrl (F1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete process.env.NEXT_PUBLIC_API_URL;
    window.localStorage.clear();
    isNativePlatform.mockReturnValue(false);
    getPlatform.mockReturnValue("web");
  });

  it("prioritizes NEXT_PUBLIC_API_URL (build-time)", () => {
    process.env.NEXT_PUBLIC_API_URL = "http://backend:9000";
    expect(getApiBaseUrl()).toBe("http://backend:9000");
  });

  it("uses the runtime override for a physical device (LAN IP)", () => {
    window.localStorage.setItem(OVERRIDE_KEY, "http://192.168.1.50:8000/");
    expect(getApiBaseUrl()).toBe("http://192.168.1.50:8000");
  });

  it("ignores a garbage override", () => {
    window.localStorage.setItem(OVERRIDE_KEY, "garbage");
    // jsdom corre en http://localhost:3000 → rama navegador localhost
    expect(getApiBaseUrl()).toBe("http://localhost:8001");
  });

  it("uses the emulator alias on native Android without override", () => {
    isNativePlatform.mockReturnValue(true);
    getPlatform.mockReturnValue("android");
    expect(getApiBaseUrl()).toBe("http://10.0.2.2:8001");
  });

  it("falls back to localhost on browser", () => {
    expect(getApiBaseUrl()).toBe("http://localhost:8001");
  });

  it("setApiBaseUrl persists for the next app start", () => {
    setApiBaseUrl("http://192.168.1.50:8000/");
    expect(getApiBaseUrl()).toBe("http://192.168.1.50:8000");
  });

  it("runtime override beats the build-time env (mobile physical device)", () => {
    process.env.NEXT_PUBLIC_API_URL = "http://prod:8000";
    window.localStorage.setItem(OVERRIDE_KEY, "http://override:9000");
    // En un APK la URL de build suele ser localhost/10.0.2.2 (no válida en un
    // móvil real), así que el override en runtime debe ganar.
    expect(getApiBaseUrl()).toBe("http://override:9000");
  });
});
