import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should redirect to login when accessing protected route without auth', async ({ page }) => {
    await page.goto('/dashboard');

    // Debe redirigir a login o mostrar pantalla de autenticación
    await expect(page).toHaveURL(/.*login|auth/);
  });

  test('should display login page with Google OAuth button', async ({ page }) => {
    await page.goto('/login');

    // Verificar que existe el botón de Google OAuth
    const googleButton = page.getByRole('button', { name: /google|iniciar sesión/i });
    await expect(googleButton).toBeVisible();
  });

  test('should allow personal mode bypass when AUTH_DISABLED is true', async ({ page }) => {
    // Este test solo funciona si NEXT_PUBLIC_AUTH_DISABLED=true en el entorno
    // Skip si no está habilitado
    test.skip(process.env.NEXT_PUBLIC_AUTH_DISABLED !== 'true', 'AUTH_DISABLED not enabled');

    await page.goto('/dashboard');

    // En modo personal, debe permitir acceso sin login
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('should handle invalid credentials gracefully', async ({ page }) => {
    await page.goto('/login');

    // Intentar login con credenciales inválidas (si hay formulario de email/password)
    const emailInput = page.getByLabel(/email|correo/i);
    const passwordInput = page.getByLabel(/contraseña|password/i);
    const submitButton = page.getByRole('button', { name: /iniciar sesión|login/i });

    if (await emailInput.isVisible()) {
      await emailInput.fill('invalid@test.com');
      await passwordInput.fill('wrongpassword');
      await submitButton.click();

      // Debe mostrar mensaje de error
      const errorMessage = page.getByText(/error|inválido|incorrecto/i);
      await expect(errorMessage).toBeVisible({ timeout: 5000 });
    }
  });
});
