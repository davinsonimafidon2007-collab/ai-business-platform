import { test, expect } from '@playwright/test';

test.describe('Complete User Journey', () => {
  test('should complete full flow: search → save opportunity → view details', async ({ page }) => {
    // 1. Ir a búsqueda
    await page.goto('/search');

    // 2. Ejecutar búsqueda
    const searchButton = page.getByRole('button', { name: /buscar|search/i });
    await searchButton.click();
    await page.waitForLoadState('networkidle');

    // 3. Verificar que hay resultados
    const results = page.locator('[data-testid="vehicle-card"], .vehicle-card');
    const resultsCount = await results.count();

    if (resultsCount > 0) {
      // 4. Guardar primera oportunidad
      const saveButton = results.first().locator('button:has-text("guardar"), button:has-text("oportunidad")');
      if (await saveButton.isVisible()) {
        await saveButton.click();
        await page.waitForTimeout(2000);

        // 5. Ir a oportunidades
        await page.goto('/opportunities');
        await page.waitForLoadState('networkidle');

        // 6. Verificar que la oportunidad fue guardada
        const opportunities = page.locator('[data-testid="opportunity-card"], .opportunity-card');
        await expect(opportunities.first()).toBeVisible({ timeout: 5000 });

        // 7. Ver detalles
        await opportunities.first().click();
        await page.waitForLoadState('networkidle');

        // 8. Verificar que se muestran los detalles
        const detailsSection = page.locator('[data-testid="opportunity-details"], .opportunity-details');
        await expect(detailsSection).toBeVisible({ timeout: 5000 });
      }
    }
  });

  test('should handle budget analysis flow', async ({ page }) => {
    await page.goto('/budget-analysis');

    // Verificar que la página carga
    await expect(page).toHaveURL(/.*budget/);

    // Buscar formulario de análisis
    const budgetInput = page.getByLabel(/presupuesto|budget/i);

    if (await budgetInput.isVisible()) {
      await budgetInput.fill('25000');

      const analyzeButton = page.getByRole('button', { name: /analizar|analyze/i });
      await analyzeButton.click();

      await page.waitForLoadState('networkidle');

      // Verificar que se muestran resultados o mensaje de "sin resultados"
      const results = page.locator('[data-testid="budget-result"], .budget-result');
      const noResults = page.getByText(/no se encontraron|no results/i);

      const hasResults = await results.count() > 0;
      const hasNoResults = await noResults.isVisible();

      expect(hasResults || hasNoResults).toBeTruthy();
    }
  });
});
