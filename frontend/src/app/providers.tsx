"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { OfflineBanner } from "@/app/hooks/use-offline";
import { ToastProvider } from "@/app/components/ui/ToastProvider";

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

  return (
    <QueryClientProvider client={queryClient}>
      <OfflineBanner />
      <ToastProvider />
      {children}
    </QueryClientProvider>
  );
}
