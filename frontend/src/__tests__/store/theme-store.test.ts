import { describe, it, expect, beforeEach, vi } from "vitest";

import { useThemeStore } from "@/app/store/theme-store";

function resetStore() {
  useThemeStore.setState({ theme: "light" });
  localStorage.clear();
  document.documentElement.classList.remove("dark");
}

/** jsdom no implementa matchMedia: hay que stubearlo, no espiarlo. */
function stubPrefersDark(matches: boolean) {
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
    localStorage.setItem("theme", "dark");
    stubPrefersDark(false);

    useThemeStore.getState().initialize();

    expect(useThemeStore.getState().theme).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("initialize falls back to the OS preference when nothing is stored", () => {
    stubPrefersDark(true);

    useThemeStore.getState().initialize();

    expect(useThemeStore.getState().theme).toBe("dark");
  });

  it("initialize defaults to light without preference", () => {
    stubPrefersDark(false);

    useThemeStore.getState().initialize();

    expect(useThemeStore.getState().theme).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});

