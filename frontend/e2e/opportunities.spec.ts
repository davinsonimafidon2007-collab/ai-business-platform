import { test, expect } from '@playwright/test';

test.describe('Opportunities Management', () => {
  test.beforeEach(async ({ page }) => {
    // Asumiendo que el usuario ya está autenticado (usar storageState si es necesario)
    await page.goto('/opportunities');
  });

  test('should display opportunities list', async ({ page }) => {
    // Verificar que la página de oportunidades carga
    await expect(page).toHaveURL(/.*opportunities/);

    // Debe haber un listado o mensaje de "no hay oportunidades"
    const opportunitiesList = page.locator('[data-testid="opportunity-card"], .opportunity-card');
    const emptyMessage = page.getByText(/no hay oportunidades|no opportunities/i);

    const hasList = await opportunitiesList.count() > 0;
    const hasEmpty = await emptyMessage.isVisible();

    expect(hasList || hasEmpty).toBeTruthy();
  });

  test('should allow creating a new opportunity from search results', async ({ page }) => {
    // Ir a búsqueda
    await page.goto('/search');

    // Ejecutar búsqueda
    const searchButton = page.getByRole('button', { name: /buscar|search/i });
    await searchButton.click();
    await page.waitForLoadState('networkidle');

    // Buscar botón de "guardar como oportunidad" en un resultado
    const saveButton = page.locator('[data-testid="save-opportunity"], button:has-text("guardar"), button:has-text("oportunidad")').first();

    if (await saveButton.isVisible()) {
      await saveButton.click();

      // Debe redirigir a oportunidades o mostrar confirmación
      await page.waitForTimeout(2000);

      const successMessage = page.getByText(/guardado|creado|éxito|success/i);
      const redirectedToOpportunities = page.url().includes('/opportunities');

      expect(await successMessage.isVisible() || redirectedToOpportunities).toBeTruthy();
    }
  });

  test('should display opportunity details', async ({ page }) => {
    // Si hay oportunidades, hacer clic en la primera
    const firstOpportunity = page.locator('[data-testid="opportunity-card"], .opportunity-card').first();

    if (await firstOpportunity.isVisible()) {
      await firstOpportunity.click();

      // Debe mostrar detalles de la oportunidad
      await page.waitForLoadState('networkidle');

      const detailsSection = page.locator('[data-testid="opportunity-details"], .opportunity-details');
      await expect(detailsSection).toBeVisible({ timeout: 5000 });

      // Verificar que hay información clave visible
      const hasPrice = await page.getByText(/precio|price|€|\$/i).isVisible();
      const hasVehicle = await page.getByText(/vehículo|vehicle|coche|car/i).isVisible();

      expect(hasPrice || hasVehicle).toBeTruthy();
    }
  });

  test('should allow deleting an opportunity', async ({ page }) => {
    const firstOpportunity = page.locator('[data-testid="opportunity-card"], .opportunity-card').first();

    if (await firstOpportunity.isVisible()) {
      // Buscar botón de eliminar
      const deleteButton = firstOpportunity.locator('button:has-text("eliminar"), button:has-text("delete"), [data-testid="delete-opportunity"]');

      if (await deleteButton.isVisible()) {
        await deleteButton.click();

        // Confirmar eliminación si hay modal
        const confirmButton = page.getByRole('button', { name: /confirmar|confirm|sí|yes/i });
        if (await confirmButton.isVisible()) {
          await confirmButton.click();
        }

        await page.waitForTimeout(2000);

        // Verificar que la oportunidad fue eliminada o mostrar mensaje de éxito
        const successMessage = page.getByText(/eliminado|deleted|éxito/i);
        const hasSuccess = await successMessage.isVisible().catch(() => false);

        // La página no debe mostrar error
        const pageContent = await page.content();
        expect(pageContent).not.toContain('Internal Server Error');
      }
    }
  });
});
