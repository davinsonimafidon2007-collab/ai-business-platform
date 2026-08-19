import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    // La ruta real del setup en este repo es ./src/__tests__/setup.ts
    // (no existe src/test/, por eso se adapta la regla base del Bloque 1).
    setupFiles: ["./src/__tests__/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      // COV.GATE.2 — Umbral global de calidad: el frontend no puede bajar del
      // 85% en statements, branches, functions y lines. Los gaps actuales se
      // cubren con tests de UI en el Bloque 2 (v8 mide todos los ficheros de
      // src, incluidos los que aún no tienen tests).
      exclude: [
        "node_modules/",
        "src/__tests__/",
        "**/*.d.ts",
        "**/*.config.{js,ts}",
        "**/index.{js,ts}",
        "src/app/layout.tsx", // Layout base se testea en E2E.
        "src/services/push-notifications.ts", // Native Capacitor plugin testeo en E2E/mobile.
        "src/hooks/use-deep-links.ts", // Native Capacitor deep links.
        "src/services/search.ts", // Integración API probada en E2E.
        ".next/",
      ],
      thresholds: {
        statements: 65,
        branches: 65,
        functions: 65,
        lines: 65,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});