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
  params?: Record<string, string>;
  queryParams?: Record<string, string>;
}

export const SCHEME = "aibusiness";
export const WEB_HOST = "aibusiness.app";

export function parseDeepLink(url: string): DeepLinkData | null {
  try {
    const urlObj = new URL(url);
    const isValidScheme =
      urlObj.protocol === "aibusiness:" ||
      urlObj.hostname === "aibusiness.app" ||
      urlObj.hostname === "app.aibusiness.com" ||
      urlObj.hostname === "aibusiness.platform";
    if (!isValidScheme) return null;

    let path = "";
    if (urlObj.protocol === "aibusiness:") {
      path = (urlObj.hostname + urlObj.pathname).replace(/^\/+/g, "").replace(/\/+$/g, "");
    } else {
      path = urlObj.pathname.replace(/^\/+/g, "").replace(/\/+$/g, "");
    }

    const queryParams: Record<string, string> = {};
    urlObj.searchParams.forEach((value, key) => {
      queryParams[key] = value;
    });
    return { path, params: queryParams, queryParams };
  } catch {
    return null;
  }
}

export function resolveDeepLinkRoute(data: DeepLinkData): string | null {
  const segments = data.path.split("/").filter(Boolean);
  if (segments.length === 0) return "/dashboard";
  const [resource, id] = segments;

  if (resource === "vehicle" && id) return `/vehicle/${id}`;
  if (resource === "deal" && id) return `/deal/${id}`;

  const withId = (route: string) => (id ? `${route}?id=${id}` : route);
  switch (resource) {
    case "vehicle":
      return withId("/vehicles");
    case "deal":
      return withId("/deals");
    case "opportunity":
      return withId("/opportunities");
    case "search": {
      // MOBILE-HARDENING #4: el builder coloca la búsqueda en el path
      // (deepLinkBuilder.search → aibusiness://search/Toyota), mientras que
      // otros productores usan query params (aibusiness://search?q=Toyota).
      // Se aceptan ambas formas: el segmento del path se convierte en el
      // parámetro "q" salvo que ya venga uno explícito.
      const sp = new URLSearchParams(data.queryParams ?? {});
      if (id && !sp.get("q")) sp.set("q", decodeURIComponent(id));
      const qs = sp.toString();
      return qs ? `/search?${qs}` : "/search";
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
    // MOBILE-HARDENING #4: cleanup robusto. Si el componente se desmonta
    // antes de que el import dinámico resuelva, `cancelled` evita registrar
    // un listener huérfano que nadie removería jamás.
    let cancelled = false;
    let listenerHandle: { remove: () => Promise<void> } | null = null;

    const initDeepLinks = async () => {
      try {
        const { App } = await import("@capacitor/app");

        // MOBILE-HARDENING #4: cold start. En arranque en frío la URL puede
        // entregarse antes de que este listener exista; getLaunchUrl()
        // devuelve esa URL inicial pendiente.
        const launch = await App.getLaunchUrl();
        if (!cancelled && launch?.url) handleDeepLink(launch.url);

        if (cancelled) return;
        listenerHandle = await App.addListener("appUrlOpen", (data) =>
          handleDeepLink(data.url)
        );
        if (cancelled) {
          void listenerHandle.remove();
          listenerHandle = null;
        }
      } catch (err) {
        console.error("[DeepLinks] init failed:", err);
      }
    };

    void initDeepLinks();
    return () => {
      cancelled = true;
      if (listenerHandle) void listenerHandle.remove();
    };
  }, [handleDeepLink]);

  return { handleDeepLink };
}

function toQuery(params?: Record<string, string>): string {
  if (!params || Object.keys(params).length === 0) return "";
  const qs = new URLSearchParams(params);
  return `?${qs.toString()}`;
}

export const deepLinkBuilder = {
  vehicle: (id: string, params?: Record<string, string>) =>
    `aibusiness://vehicle/${id}${toQuery(params)}`,
  deal: (id: string, params?: Record<string, string>) =>
    `aibusiness://deal/${id}${toQuery(params)}`,
  opportunity: (id: string) => `aibusiness://opportunity/${id}`,
  search: (query: string, params?: Record<string, string>) =>
    `aibusiness://search/${encodeURIComponent(query)}${toQuery(params)}`,
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
