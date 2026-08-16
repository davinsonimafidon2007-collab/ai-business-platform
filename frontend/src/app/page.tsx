"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/app/store/auth-store";
import { isAuthDisabled } from "@/app/config/app-mode";
import { LAST_PATH_KEY } from "@/app/components/auth/auth-guard";

const APP_PATHS = [
  "/dashboard",
  "/search",
  "/vehicles",
  "/history",
  "/inspection",
  "/opportunities",
  "/deals",
  "/admin",
  "/api-keys",
];

function lastVisitedPath(): string | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(LAST_PATH_KEY);
  if (!raw) return null;
  const path = raw.startsWith("/") ? raw : `/${raw}`;
  return APP_PATHS.some((prefix) => path.startsWith(prefix)) ? path : null;
}

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, isLoading, initialize } = useAuthStore();
  // Uso personal (PERS.CLOSE.1): no hay landing de login, directo al dashboard
  // o a la última ruta visitada (PERSONAL.NOAUTH).
  const authDisabled = isAuthDisabled();

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (authDisabled) {
      router.replace(lastVisitedPath() ?? "/dashboard/");
      return;
    }
    if (!isLoading && isAuthenticated) {
      router.push("/dashboard/");
    }
  }, [authDisabled, isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
          <p className="mt-2 text-secondary-600">Cargando...</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-8">
      <main className="flex flex-col items-center gap-8">
        <h1 className="text-4xl font-bold text-primary-600 dark:text-primary-400">
          AI Business Platform
        </h1>
        <p className="text-lg text-secondary-600 dark:text-secondary-400 text-center max-w-md">
          Vehicle import analysis and market intelligence platform
        </p>
        <div className="flex gap-4">
          <Link
            href="/auth/login/"
            className="rounded-lg bg-primary-600 px-6 py-3 text-white font-medium hover:bg-primary-700 transition-colors"
          >
            Iniciar Sesión
          </Link>
          <Link
            href="/auth/register/"
            className="rounded-lg border border-primary-600 px-6 py-3 text-primary-600 font-medium hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors"
          >
            Registrarse
          </Link>
        </div>
      </main>
    </div>
  );
}