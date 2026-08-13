import { create } from "zustand";

type Theme = "light" | "dark";

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
  initialize: () => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: "light",
  toggleTheme: () =>
    set((state) => {
      const newTheme = state.theme === "light" ? "dark" : "light";
      if (typeof window !== "undefined") {
        localStorage.setItem("theme", newTheme);
        document.documentElement.classList.toggle("dark", newTheme === "dark");
      }
      return { theme: newTheme };
    }),
  setTheme: (theme) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("theme", theme);
      document.documentElement.classList.toggle("dark", theme === "dark");
    }
    set({ theme });
  },
  initialize: () => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("theme") as Theme | null;
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const theme = stored || (mediaQuery.matches ? "dark" : "light");
      document.documentElement.classList.toggle("dark", theme === "dark");
      set({ theme });

      // Escuchar cambios de tema del sistema nativo en tiempo real (TASK-020)
      const listener = (e: MediaQueryListEvent) => {
        const hasStored = localStorage.getItem("theme");
        if (!hasStored) {
          const newTheme = e.matches ? "dark" : "light";
          document.documentElement.classList.toggle("dark", newTheme === "dark");
          set({ theme: newTheme });
        }
      };

      if (mediaQuery.addEventListener) {
        try {
          mediaQuery.addEventListener("change", listener);
        } catch (err) {
          if (mediaQuery.addListener) {
            mediaQuery.addListener(listener);
          }
        }
      } else if (mediaQuery.addListener) {
        mediaQuery.addListener(listener);
      }
    }
  },
}));