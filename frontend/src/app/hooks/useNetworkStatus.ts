"use client";

import { useEffect, useState, useCallback } from "react";

/**
 * MOB-P2-006: Hook para detectar estado de red y fallback offline.
 *
 * Cuando la red está caída, las queries pueden servir datos stale desde
 * localStorage (via useCachedQuery) en lugar de mostrar error inmediato.
 */

export type NetworkStatus = "online" | "offline" | "unknown";

function getNetworkStatus(): NetworkStatus {
  if (typeof window === "undefined") return "unknown";
  return navigator.onLine ? "online" : "offline";
}

/**
 * Devuelve el estado actual de la red y se re-actualiza automáticamente
 * cuando cambia la conectividad.
 */
export function useNetworkStatus(): NetworkStatus {
  const [status, setStatus] = useState<NetworkStatus>(getNetworkStatus);

  useEffect(() => {
    const handleOnline = () => setStatus("online");
    const handleOffline = () => setStatus("offline");

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return status;
}

/**
 * Wrapper para fetch que fallback a stale cache cuando está offline.
 * Úsalo en queries críticas (dashboard, opportunities) para mejorar UX.
 */
export function offlineFetch<T>(
  fetcher: () => Promise<T>,
  staleData: T | null,
  isOnline: boolean
): Promise<T> {
  if (!isOnline && staleData !== null) {
    return Promise.resolve(staleData);
  }
  return fetcher();
}
