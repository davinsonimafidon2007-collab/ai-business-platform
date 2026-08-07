"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/app/store/auth-store";
import { isAuthDisabled } from "@/app/config/app-mode";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuthStore();
  // Fuente de verdad única del bypass (PERS.CLOSE.1): NEXT_PUBLIC_AUTH_DISABLED.
  const authDisabled = isAuthDisabled();

  useEffect(() => {
    if (authDisabled) return;
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login/");
    }
  }, [authDisabled, isAuthenticated, isLoading, router]);

  // Auth desactivada (uso personal): siempre renderiza children, sin login.
  if (authDisabled) {
    return <>{children}</>;
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="border-t-4 border-primary-600 border-b-4 border-rounded-full w-8 h-8 animate-spin"></div>
          <p className="mt-2 text-secondary-600">Cargando...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
