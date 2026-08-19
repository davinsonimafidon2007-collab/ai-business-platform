"use client";

import { useNetworkStatus as useNetworkStatusBase, NetworkStatusType } from "@/hooks/useNetworkStatus";

export type NetworkStatus = NetworkStatusType;

export function useNetworkStatus() {
  return useNetworkStatusBase();
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
