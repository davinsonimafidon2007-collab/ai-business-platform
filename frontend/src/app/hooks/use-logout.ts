"use client";

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore, TOKEN_KEYS } from "@/app/store/auth-store";
import { secureStorage } from "@/app/services/storage";
import { api } from "@/app/services/api/client";
import { isAuthDisabled } from "@/app/config/app-mode";
import { signOutOfGoogle } from "@/app/services/google-auth";
import { unregisterPushNotifications } from "@/app/services/push-notifications";

/**
 * Path canónico de logout.
 *
 * Garantiza que, además de limpiar tokens + store (auth.logout), se vacíe la
 * caché de React Query (queryClient.clear()) para no mostrar datos del usuario
 * anterior tras un nuevo login. Debe usarse en toda la UI (navbar/dashboard).
 *
 * TASK 4/6 (AUD-015): también revoca el refresh token en el servidor
 * (POST /auth/logout). Antes solo se borraba el token local, así que el
 * refresh token seguía siendo válido en el backend tras "cerrar sesión".
 */
export function useLogout() {
  const queryClient = useQueryClient();
  const logoutStore = useAuthStore((state) => state.logout);

  return useCallback(async () => {
    // Revocación server-side del refresh token (best-effort: si falla la red
    // se sigue cerrando la sesión localmente). En modo personal no hay
    // sesión que revocar.
    if (!isAuthDisabled()) {
      try {
        const refreshToken = await secureStorage.get(TOKEN_KEYS.refreshToken);
        await api.post("/auth/logout", refreshToken ? { refresh_token: refreshToken } : {});
      } catch {
        // Ignore network/API errors: el logout local no debe bloquearse
      }
    }
    try {
      await signOutOfGoogle();
    } catch {
      // Ignore Firebase sign-out errors
    }
    try {
      await unregisterPushNotifications();
    } catch {
      // Ignore push unregister errors
    }
    queryClient.clear();
    await logoutStore();
  }, [queryClient, logoutStore]);
}
