"use client";

import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/app/store/auth-store";
import { useThemeStore } from "@/app/store/theme-store";
import { initGoogleAuth } from "@/app/services/google-auth";

function ThemeInitializer({ children }: { children: React.ReactNode }) {
  const initialize = useThemeStore((state) => state.initialize);

  useEffect(() => {
    initialize();
  }, [initialize]);

  return <>{children}</>;
}

function AuthInitializer({ children }: { children: React.ReactNode }) {
  const initialize = useAuthStore((state) => state.initialize);
  const logout = useAuthStore((state) => state.logout);
  const queryClient = useQueryClient();

  useEffect(() => {
    initialize();

    // Escucha el evento "auth:logout" que emite el API client cuando un refresh
    // falla (401). Evita importar el store desde el client (sin dependencia
    // circular) y garantiza que store + query cache queden coherentes.
    const onAuthLogout = () => {
      queryClient.clear();
      logout();
    };
    window.addEventListener("auth:logout", onAuthLogout);
    return () => window.removeEventListener("auth:logout", onAuthLogout);
  }, [initialize, logout, queryClient]);

  return <>{children}</>;
}

function GoogleAuthInitializer({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    initGoogleAuth();
  }, []);

  return <>{children}</>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeInitializer>
        <AuthInitializer>
          <GoogleAuthInitializer>{children}</GoogleAuthInitializer>
        </AuthInitializer>
      </ThemeInitializer>
    </QueryClientProvider>
  );
}