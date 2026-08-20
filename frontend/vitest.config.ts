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
      // 85% en statements, functions y lines, y 80% en branches.
      // Los componentes visuales, páginas Next.js y servicios nativos se
      // verifican en E2E Playwright.
      exclude: [
        "node_modules/",
        "src/__tests__/",
        "**/*.d.ts",
        "**/*.config.{js,ts}",
        "**/index.{js,ts}",
        "src/app/layout.tsx",
        "src/app/**/page.tsx",
        "src/app/**/layout.tsx",
        "src/app/features/**",
        "src/app/components/**",
        "src/components/**",
        "src/app/services/push-notifications.ts",
        "src/app/services/search.ts",
        "src/app/hooks/use-deep-links.ts",
        ".next/",
      ],
      thresholds: {
        statements: 85,
        branches: 80,
        functions: 85,
        lines: 85,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
