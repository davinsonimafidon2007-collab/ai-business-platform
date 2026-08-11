"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { App as CapApp } from "@capacitor/app";
import { Capacitor } from "@capacitor/core";

/** Rutas raíz: atrás aquí puede salir de la app (o no-op). */
const ROOT_PATHS = new Set([
  "/",
  "/dashboard",
  "/search",
  "/opportunities",
  "/deals",
  "/vehicles",
  "/inspection",
  "/history",
  "/api-keys",
  "/admin",
  "/admin/api-keys",
]);

function isRootPath(pathname: string): boolean {
  if (ROOT_PATHS.has(pathname)) return true;
  // normalizar trailing slash
  const p =
    pathname.endsWith("/") && pathname.length > 1
      ? pathname.slice(0, -1)
      : pathname;
  return ROOT_PATHS.has(p);
}

/**
 * MOBILE.NAV.1 — Intercepta el botón atrás de Android.
 * - Si hay historial in-app → router.back()
 * - Si estamos en ruta raíz → no cerramos a la fuerza; opcional: minimizar (default: prevent default only)
 */
export function useAndroidBackButton(): void {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;

    const handle = CapApp.addListener("backButton", ({ canGoBack }) => {
      // Preferir historial del WebView / Next
      if (
        typeof window !== "undefined" &&
        window.history.length > 1 &&
        !isRootPath(pathname)
      ) {
        router.back();
        return;
      }
      if (canGoBack && !isRootPath(pathname)) {
        router.back();
        return;
      }
      // En raíz: no llamar App.exitApp() salvo que el producto lo pida explícitamente.
      // Evita el “me saca de la app” al navegar mal.
    });

    return () => {
      void handle.then((h) => h.remove());
    };
  }, [router, pathname]);
}