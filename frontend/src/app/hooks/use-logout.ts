"use client";

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/app/store/auth-store";
import { signOutOfGoogle } from "@/app/services/google-auth";
import { teardownPushNotifications } from "@/app/services/push-notifications";

/**
 * Path canónico de logout.
 *
 * Garantiza que, además de limpiar tokens + store (auth.logout), se vacíe la
 * caché de React Query (queryClient.clear()) para no mostrar datos del usuario
 * anterior tras un nuevo login. Debe usarse en toda la UI (navbar/dashboard).
 */
export function useLogout() {
  const queryClient = useQueryClient();
  const logoutStore = useAuthStore((state) => state.logout);

  return useCallback(async () => {
    try {
      await signOutOfGoogle();
    } catch {
      // Ignore Firebase sign-out errors
    }
    try {
      // MOBILE-HARDENING #5: teardown completo (unregister backend + remover
      // listeners + reset de estado para poder re-inicializar tras re-login).
      await teardownPushNotifications();
    } catch {
      // Ignore push unregister errors
    }
    queryClient.clear();
    await logoutStore();
  }, [queryClient, logoutStore]);
}
