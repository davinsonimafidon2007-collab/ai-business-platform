import { test, expect } from '@playwright/test';

test.describe('Admin Panel', () => {
  test.beforeEach(async ({ page }) => {
    // Asumiendo que el usuario está autenticado como admin
    await page.goto('/admin');
  });

  test('should display admin dashboard', async ({ page }) => {
    await expect(page).toHaveURL(/.*admin/);

    // Regresión: el markup real no usa data-testid ni clases .admin-metric/
    // .admin-dashboard (confirmado corriendo este spec contra la app real,
    // y leyendo app/(app)/admin/page.tsx: es AdminStatusPage, sin testids).
    // Se asertan las secciones reales que siempre renderiza esa página.
    await expect(page.getByText('Admin · Sistema')).toBeVisible();
    await expect(page.getByText('PROVIDER CANARY')).toBeVisible({ timeout: 10_000 });
  });

  test('should allow viewing system status', async ({ page }) => {
    // La página /admin ES la página de estado del sistema (no hay un link
    // separado "estado/status/sistema" — regresión: el link buscado antes
    // nunca existió, así que el test "pasaba" sin comprobar nada).
    await expect(page.getByText('Health', { exact: true })).toBeVisible();
    await expect(page.getByText(/api: ok|api: error/i)).toBeVisible({ timeout: 10_000 });
  });
});
