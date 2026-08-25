import { isAuthDisabled, LOCAL_USER } from "@/app/config/app-mode";

describe("config/app-mode (PERSONAL.NOAUTH)", () => {
  const ORIGINAL_ENV = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...ORIGINAL_ENV };
  });

  afterAll(() => {
    process.env = ORIGINAL_ENV;
  });

  describe("isAuthDisabled", () => {
    it("es false por defecto (multi-user con login)", () => {
      delete process.env.NEXT_PUBLIC_AUTH_DISABLED;
      expect(isAuthDisabled()).toBe(false);
    });

    it("solo es true con NEXT_PUBLIC_AUTH_DISABLED=true exacto", () => {
      process.env.NEXT_PUBLIC_AUTH_DISABLED = "true";
      expect(isAuthDisabled()).toBe(true);

      process.env.NEXT_PUBLIC_AUTH_DISABLED = "TRUE";
      expect(isAuthDisabled()).toBe(false);

      process.env.NEXT_PUBLIC_AUTH_DISABLED = "1";
      expect(isAuthDisabled()).toBe(false);
    });
  });

  describe("LOCAL_USER (contrato con el backend)", () => {
    // Debe coincidir con app/core/local_user.py del backend.
    const BACKEND_LOCAL_USER_ID = "00000000-0000-4000-8000-000000000001";
    const BACKEND_LOCAL_USER_EMAIL = "local@example.com";

    it("usa el UUID y email fijos del usuario local ADMIN", () => {
      expect(LOCAL_USER.id).toBe(BACKEND_LOCAL_USER_ID);
      expect(LOCAL_USER.email).toBe(BACKEND_LOCAL_USER_EMAIL);
    });

    it("role usa el VALUE del enum backend en minúsculas ('admin')", () => {
      // El wire format de UserRead serializa Role por value ("admin"), no por
      // nombre ("ADMIN"). La UI compara contra este valor.
      expect(LOCAL_USER.role).toBe("admin");
    });

    it("es un usuario verificado (entrada directa sin login)", () => {
      expect(LOCAL_USER.is_verified).toBe(true);
      expect(LOCAL_USER.full_name).toBe("Local Admin");
    });
  });
});
