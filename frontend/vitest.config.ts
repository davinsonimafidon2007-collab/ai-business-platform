import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/__tests__/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    // COV.GATE.1 — gate acotado a store/** y services/**, que es la lógica
    // con tests unitarios razonables. Los componentes y páginas quedan fuera
    // hasta que haya tests de UI (task aparte).
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      include: ["src/app/store/**", "src/app/services/**"],
      exclude: [
        "node_modules/**",
        "src/__tests__/**",
        // Wrapper de axios (interceptores, refresh, redirects): necesita un
        // harness de red que no aporta aquí. Se cubrirá con tests de
        // integración del cliente HTTP.
        "src/app/services/api/client.ts",
      ],
      thresholds: {
        lines: 30,
        functions: 30,
        branches: 20,
        statements: 30,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});