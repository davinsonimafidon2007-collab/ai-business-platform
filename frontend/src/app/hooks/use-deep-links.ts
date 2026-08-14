"use client";

/**
 * MOB-P1-009: Deep Link Service
 * Navegación desde push notifications y URLs externas.
 */

import { useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Capacitor } from "@capacitor/core";

export interface DeepLinkData {
  path: string;
  queryParams: Record<string, string>;
}

export function parseDeepLink(url: string): DeepLinkData | null {
  try {
    const urlObj = new URL(url);
    const isValidScheme =
      urlObj.protocol === "aibusiness:" ||
      urlObj.hostname === "aibusiness.app" ||
      urlObj.hostname === "app.aibusiness.com" ||
      urlObj.hostname === "aibusiness.platform";
    if (!isValidScheme) return null;
    const path = urlObj.pathname.replace(/^\/+/g, "");
    const queryParams: Record<string, string> = {};
    urlObj.searchParams.forEach((value, key) => {
      queryParams[key] = value;
    });
    return { path, queryParams };
  } catch {
    return null;
  }
}

export function resolveDeepLinkRoute(data: DeepLinkData): string | null {
  const segments = data.path.split("/").filter(Boolean);
  if (segments.length === 0) return "/dashboard";
  const [resource, id] = segments;
  // El repo no tiene rutas dinámicas de detalle ([id]); mapeamos los recursos
  // a las rutas de listado existentes, pasando el id como query param cuando
  // esté disponible (p.ej. aibusiness://deal/42 → /deals?id=42).
  const withId = (route: string) => (id ? `${route}?id=${id}` : route);
  switch (resource) {
    case "vehicle":
      return withId("/vehicles");
    case "deal":
      return withId("/deals");
    case "opportunity":
      return withId("/opportunities");
    case "search": {
      const params = new URLSearchParams(data.queryParams).toString();
      return params ? `/search?${params}` : "/search";
    }
    case "settings":
      return "/settings";
    case "dashboard":
    case "home":
      return "/dashboard";
    default:
      return null;
  }
}

export function useDeepLinks() {
  const router = useRouter();

  const handleDeepLink = useCallback(
    (url: string) => {
      const data = parseDeepLink(url);
      if (!data) return;
      const route = resolveDeepLinkRoute(data);
      if (route) router.push(route);
    },
    [router]
  );

  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;
    let removeListener: (() => void) | null = null;

    const initDeepLinks = async () => {
      const { App } = await import("@capacitor/app");
      const listener = await App.addListener("appUrlOpen", (data) => handleDeepLink(data.url));
      removeListener = listener.remove;
    };

    void initDeepLinks();
    return () => {
      if (removeListener) removeListener();
    };
  }, [handleDeepLink]);

  return { handleDeepLink };
}

export const deepLinkBuilder = {
  vehicle: (id: string) => `aibusiness://vehicle/${id}`,
  deal: (id: string) => `aibusiness://deal/${id}`,
  opportunity: (id: string) => `aibusiness://opportunity/${id}`,
  search: (params: Record<string, string>) => {
    const qs = new URLSearchParams(params).toString();
    return `aibusiness://search?${qs}`;
  },
  settings: () => `aibusiness://settings`,
  dashboard: () => `aibusiness://dashboard`,
};

export function useShare() {
  const share = useCallback(async (options: { title: string; text: string; url?: string; dialogTitle?: string }) => {
    if (!Capacitor.isNativePlatform()) {
      if (navigator.clipboard && options.url) {
        await navigator.clipboard.writeText(options.url);
      }
      return;
    }
    try {
      const { Share } = await import("@capacitor/share");
      await Share.share({ title: options.title, text: options.text, url: options.url, dialogTitle: options.dialogTitle || "Compartir" });
    } catch (err) {
      console.error("[Share] Failed:", err);
    }
  }, []);

  return { share };
}
