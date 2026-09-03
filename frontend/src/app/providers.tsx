"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { OfflineBanner } from "@/app/hooks/use-offline";
import { ToastProvider } from "@/app/components/ui/ToastProvider";
import { useThemeStore } from "@/app/store/theme-store";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: (failureCount, error) => {
              if (error instanceof Error && error.message.includes("401")) return false;
              if (error instanceof Error && error.message.includes("429")) return false;
              return failureCount < 2;
            },
          },
        },
      })
  );

  // Bug real preexistente: theme-store.initialize() nunca se llamaba desde
  // ningún sitio de la app — la preferencia guardada (o el default oscuro)
  // nunca se aplicaba al cargar, solo tras tocar el toggle manualmente.
  const initializeTheme = useThemeStore((s) => s.initialize);
  useEffect(() => {
    initializeTheme();
  }, [initializeTheme]);

  return (
    <QueryClientProvider client={queryClient}>
      <OfflineBanner />
      <ToastProvider />
      {children}
    </QueryClientProvider>
  );
}
