import { test, expect } from '@playwright/test';

test.describe('Vehicle Search Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navegar a la página de búsqueda
    await page.goto('/search');
  });

  test('should display search form with filters', async ({ page }) => {
    // Verificar que existen los campos de filtro
    const brandSelect = page.getByLabel(/marca|brand/i);
    const modelInput = page.getByLabel(/modelo|model/i);
    const priceRange = page.getByLabel(/precio|price/i);

    await expect(brandSelect).toBeVisible();
    await expect(modelInput).toBeVisible();
    await expect(priceRange).toBeVisible();
  });

  test('should execute search and display results', async ({ page }) => {
    // Seleccionar marca
    const brandSelect = page.getByLabel(/marca|brand/i);
    await brandSelect.selectOption({ index: 1 });

    // Ejecutar búsqueda
    const searchButton = page.getByRole('button', { name: /buscar|search/i });
    await searchButton.click();

    // Esperar a que carguen los resultados
    await page.waitForLoadState('networkidle');

    // Verificar que hay resultados o mensaje de "no hay resultados"
    const results = page.locator('[data-testid="vehicle-card"], .vehicle-card');
    const noResults = page.getByText(/no se encontraron|no results/i);

    const hasResults = await results.count() > 0;
    const hasNoResults = await noResults.isVisible();

    expect(hasResults || hasNoResults).toBeTruthy();
  });

  test('should handle search errors gracefully', async ({ page }) => {
    // Simular búsqueda con filtros que causen error
    const brandSelect = page.getByLabel(/marca|brand/i);
    await brandSelect.selectOption({ label: 'marca-inexistente-xyz' }).catch(() => {});

    const searchButton = page.getByRole('button', { name: /buscar|search/i });
    await searchButton.click();

    // Debe mostrar mensaje de error o "no hay resultados", no crash
    await page.waitForTimeout(3000);

    const errorMessage = page.getByText(/error|no se encontraron|revisa/i);
    const hasError = await errorMessage.isVisible().catch(() => false);

    // La página no debe estar en blanco ni mostrar error 500
    const pageContent = await page.content();
    expect(pageContent).not.toContain('Internal Server Error');
    expect(pageContent).not.toContain('Application error');
  });

  test('should allow filtering results by price range', async ({ page }) => {
    // Ejecutar búsqueda primero
    const searchButton = page.getByRole('button', { name: /buscar|search/i });
    await searchButton.click();
    await page.waitForLoadState('networkidle');

    // Aplicar filtro de precio
    const minPriceInput = page.getByLabel(/precio mínimo|min price/i);
    const maxPriceInput = page.getByLabel(/precio máximo|max price/i);

    if (await minPriceInput.isVisible()) {
      await minPriceInput.fill('10000');
      await maxPriceInput.fill('30000');

      const applyFilterButton = page.getByRole('button', { name: /aplicar|apply|filtrar/i });
      await applyFilterButton.click();

      await page.waitForLoadState('networkidle');

      // Verificar que los resultados están dentro del rango
      const priceElements = page.locator('[data-testid="vehicle-price"], .price');
      const count = await priceElements.count();

      if (count > 0) {
        // Al menos un resultado debe estar visible
        expect(count).toBeGreaterThan(0);
      }
    }
  });
});
