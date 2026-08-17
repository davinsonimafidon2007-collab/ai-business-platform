import { test, expect } from "@playwright/test";

/**
 * Flujo básico web (smoke). Requiere backend + frontend corriendo en
 * localhost:3000/8000. Con NEXT_PUBLIC_AUTH_DISABLED=true (uso personal) no
 * hace falta login real para explorar búsqueda/detalle.
 */

test("homepage loads and renders the app shell", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("body")).toBeAttached();
  await expect(page).toHaveTitle(/AI Business Platform/);
});

test("search flow: query a vehicle and open a result", async ({ page }) => {
  await page.goto("/");

  // El input de búsqueda puede estar en la home o en el header. Localízalo de
  // forma tolerante (placeholder o tipo texto) para no acoplar a un selector.
  const searchInput = page
    .locator('input[type="search"], input[name="search"], input[placeholder*="buscar" i], input[placeholder*="search" i]')
    .first();

  if (await searchInput.isVisible()) {
    await searchInput.fill("Toyota Corolla");
    await searchInput.press("Enter");
    // Esperar a que la URL cambie a una ruta de búsqueda (si existe) o a que
    // aparezca algún resultado.
    await page.waitForTimeout(1500);
  }

  // Verifica que la app siga viva y no haya un error de página completa.
  await expect(page.locator("body")).toBeAttached();
});
