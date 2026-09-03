import { describe, it, expect, beforeEach, vi } from "vitest";

import { useThemeStore } from "@/app/store/theme-store";

function resetStore() {
  useThemeStore.setState({ theme: "light" });
  localStorage.clear();
  document.documentElement.classList.remove("dark");
}

/** jsdom no implementa matchMedia: hay que stubearlo, no espiarlo.
 * El store consulta `(prefers-color-scheme: light)` (el oscuro es el
 * default; solo se cae a claro si el sistema lo pide explícitamente). */
function stubPrefersLight(matches: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockReturnValue({ matches } as MediaQueryList)
  );
}

describe("useThemeStore", () => {
  beforeEach(resetStore);

  it("toggles light -> dark and persists", () => {
    useThemeStore.getState().toggleTheme();

    expect(useThemeStore.getState().theme).toBe("dark");
    expect(localStorage.getItem("theme")).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("toggles back dark -> light and removes the class", () => {
    useThemeStore.getState().toggleTheme();
    useThemeStore.getState().toggleTheme();

    expect(useThemeStore.getState().theme).toBe("light");
    expect(localStorage.getItem("theme")).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("setTheme applies the given theme", () => {
    useThemeStore.getState().setTheme("dark");

    expect(useThemeStore.getState().theme).toBe("dark");
    expect(localStorage.getItem("theme")).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("initialize prefers the stored value over the OS preference", () => {
    localStorage.setItem("theme", "light");
    stubPrefersLight(false);

    useThemeStore.getState().initialize();

    expect(useThemeStore.getState().theme).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("initialize falls back to light when the OS explicitly prefers light and nothing is stored", () => {
    stubPrefersLight(true);

    useThemeStore.getState().initialize();

    expect(useThemeStore.getState().theme).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("initialize defaults to dark without any OS preference or stored value", () => {
    stubPrefersLight(false);

    useThemeStore.getState().initialize();

    expect(useThemeStore.getState().theme).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });
});

describe("useThemeStore SSR branches", () => {
  it("toggleTheme runs without window (SSR)", () => {
    vi.stubGlobal("window", undefined);
    try {
      useThemeStore.setState({ theme: "light" });
      useThemeStore.getState().toggleTheme();
      expect(useThemeStore.getState().theme).toBe("dark");
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("setTheme runs without window (SSR)", () => {
    vi.stubGlobal("window", undefined);
    try {
      useThemeStore.getState().setTheme("dark");
      expect(useThemeStore.getState().theme).toBe("dark");
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("initialize runs without window (SSR) and keeps the current theme", () => {
    vi.stubGlobal("window", undefined);
    try {
      useThemeStore.setState({ theme: "light" });
      useThemeStore.getState().initialize();
      expect(useThemeStore.getState().theme).toBe("light");
    } finally {
      vi.unstubAllGlobals();
    }
  });
});

