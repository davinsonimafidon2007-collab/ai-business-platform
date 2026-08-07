"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/app/store/auth-store";

const IS_PERSONAL_MODE = process.env.NEXT_PUBLIC_APP_MODE === "personal";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuthStore();

  useEffect(() => {
    if (IS_PERSONAL_MODE) return;
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/login/");
    }
  }, [isAuthenticated, isLoading, router]);

  if (IS_PERSONAL_MODE) {
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
