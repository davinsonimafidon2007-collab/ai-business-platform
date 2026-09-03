import { create } from "zustand";

type Theme = "light" | "dark";

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
  initialize: () => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  // Oscuro por defecto: es la identidad visual de la plataforma (ver
  // diseño de agents/AgentCard, ya construidas solo en oscuro). El toggle
  // sigue disponible y la preferencia guardada en localStorage manda.
  theme: "dark",
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
      // Sin preferencia guardada -> oscuro (identidad de la plataforma),
      // salvo que el sistema pida explícitamente claro (respeta esa señal
      // en el primer arranque; a partir de ahí manda el toggle guardado).
      const mediaQueryLight = window.matchMedia("(prefers-color-scheme: light)");
      const theme = stored || (mediaQueryLight.matches ? "light" : "dark");
      document.documentElement.classList.toggle("dark", theme === "dark");
      set({ theme });
    }
  },
}));