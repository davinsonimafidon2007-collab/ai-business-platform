import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E (web). El proyecto ya dispone de flujos Maestro (móvil) en
 * `e2e/*.yaml`; este runner aporta E2E de navegador para CI web.
 *
 * Para ejecutar localmente:
 *   1. Levanta backend + frontend (docker compose up o `npm run dev`).
 *   2. npx playwright install chromium   # descarga el navegador (1 vez)
 *   3. npx playwright test
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
