// Detección de modo (PERSONAL.NOAUTH): uso personal sin login.
//
// NEXT_PUBLIC_AUTH_DISABLED=true  → el frontend no exige token, no redirige a
// login y no muestra acciones de sesión. El backend, con AUTH_DISABLED=true,
// inyecta el usuario local ADMIN (get-or-create) y responde sin Bearer.
import type { User } from "@/app/types/auth";

export const isAuthDisabled = (): boolean =>
  process.env.NEXT_PUBLIC_AUTH_DISABLED === "true";

// Usuario local sintético (coincide con app/core/local_user.py del backend).
export const LOCAL_USER: User = {
  id: "00000000-0000-4000-8000-000000000001",
  email: "local@localhost",
  full_name: "Local Admin",
  is_verified: true,
  role: "ADMIN",
  created_at: new Date(0).toISOString(),
};
