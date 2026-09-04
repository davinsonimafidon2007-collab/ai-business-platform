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
// Si PLAYWRIGHT_BASE_URL viene definido, significa que ya hay un stack real
// corriendo ahí (p.ej. el job "docker build + stack smoke" de CI, que ya
// levantó api+frontend en contenedores) y Playwright NO debe intentar
// arrancar su propio `npm run dev`. Bug real que esto evita: con
// CI=true, `reuseExistingServer: !process.env.CI` da false, así que
// Playwright intentaba levantar un segundo servidor en el mismo puerto
// 3001 que el frontend de Docker ya ocupaba.
const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["list"]],
  use: {
    baseURL: externalBaseUrl || "http://localhost:3001",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: externalBaseUrl
    ? undefined
    : {
        command: "npm run dev -- -p 3001",
        url: "http://localhost:3001",
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
