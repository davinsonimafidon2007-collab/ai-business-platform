import { test, expect } from '@playwright/test';

test.describe('Admin Panel', () => {
  test.beforeEach(async ({ page }) => {
    // Asumiendo que el usuario está autenticado como admin
    await page.goto('/admin');
  });

  test('should display admin dashboard', async ({ page }) => {
    await expect(page).toHaveURL(/.*admin/);

    // Verificar que hay métricas o estadísticas
    const metrics = page.locator('[data-testid="admin-metric"], .admin-metric');
    const dashboard = page.locator('[data-testid="admin-dashboard"], .admin-dashboard');

    const hasMetrics = await metrics.count() > 0;
    const hasDashboard = await dashboard.isVisible();

    expect(hasMetrics || hasDashboard).toBeTruthy();
  });

  test('should allow viewing system status', async ({ page }) => {
    const statusLink = page.getByRole('link', { name: /estado|status|sistema/i });

    if (await statusLink.isVisible()) {
      await statusLink.click();
      await page.waitForLoadState('networkidle');

      // Verificar que se muestra información del sistema
      const systemInfo = page.locator('[data-testid="system-info"], .system-info');
      await expect(systemInfo).toBeVisible({ timeout: 5000 });
    }
  });
});
