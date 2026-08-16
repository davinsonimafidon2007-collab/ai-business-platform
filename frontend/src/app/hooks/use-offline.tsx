"use client";

/**
 * MOB-P1-008: Offline Service
 * Cache de búsquedas y detección de red en tiempo real.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { Capacitor } from "@capacitor/core";
import { secureStorage } from "@/app/services/storage";

const OFFLINE_CACHE_KEY = "abp_offline_cache";
const MAX_CACHED_SEARCHES = 20;

export interface CachedSearch {
  id: string;
  query: Record<string, unknown>;
  results: unknown[];
  timestamp: number;
  resultCount: number;
}
export interface OfflineState {
  isOnline: boolean;
  connectionType: string;
}

/**
 * Estado de red en tiempo real. En nativo usa @capacitor/network; en web
 * usa navigator.onLine. (El hook `useNetworkStatus` de hooks/useNetworkStatus
 * ya cubre el caso web puro; este añade el tipo de conexión Capacitor.)
 */
export function useNetworkStatus(): OfflineState {
  const [state, setState] = useState<OfflineState>({ isOnline: true, connectionType: "unknown" });

  useEffect(() => {
    let removeListener: (() => void) | null = null;

    const initNetwork = async () => {
      if (!Capacitor.isNativePlatform()) {
        const updateOnline = () =>
          setState({ isOnline: navigator.onLine, connectionType: navigator.onLine ? "wifi" : "none" });
        window.addEventListener("online", updateOnline);
        window.addEventListener("offline", updateOnline);
        updateOnline();
        return;
      }
      const { Network } = await import("@capacitor/network");
      const status = await Network.getStatus();
      setState({ isOnline: status.connected, connectionType: status.connectionType });
      const listener = await Network.addListener("networkStatusChange", (status) =>
        setState({ isOnline: status.connected, connectionType: status.connectionType })
      );
      removeListener = listener.remove;
    };

    void initNetwork();
    return () => {
      if (removeListener) removeListener();
    };
  }, []);

  return state;
}

export const offlineCache = {
  async getAll(): Promise<CachedSearch[]> {
    const raw = await secureStorage.get(OFFLINE_CACHE_KEY);
    if (!raw) return [];
    try {
      return JSON.parse(raw);
    } catch {
      return [];
    }
  },
  async add(search: Omit<CachedSearch, "id" | "timestamp">): Promise<void> {
    const cached = await this.getAll();
    const newEntry: CachedSearch = {
      ...search,
      id: `search_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
    };
    const deduped = cached.filter((c) => JSON.stringify(c.query) !== JSON.stringify(search.query));
    await secureStorage.set(OFFLINE_CACHE_KEY, JSON.stringify([newEntry, ...deduped].slice(0, MAX_CACHED_SEARCHES)));
  },
  async findByQuery(query: Record<string, unknown>): Promise<CachedSearch | null> {
    const cached = await this.getAll();
    return cached.find((c) => JSON.stringify(c.query) === JSON.stringify(query)) || null;
  },
  async clear(): Promise<void> {
    await secureStorage.remove(OFFLINE_CACHE_KEY);
  },
  async getRecent(limit = 5): Promise<CachedSearch[]> {
    return (await this.getAll()).slice(0, limit);
  },
};

export function useOfflineSearch<T>(
  queryFn: () => Promise<T>,
  queryKey: string,
  queryParams: Record<string, unknown>,
  options?: { enabled?: boolean }
) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [isOfflineData, setIsOfflineData] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const { isOnline } = useNetworkStatus();
  const queryParamsKey = JSON.stringify(queryParams);
  const stableQueryParams = useMemo(() => JSON.parse(queryParamsKey) as Record<string, unknown>, [queryParamsKey]);

  const execute = useCallback(async () => {
    if (options?.enabled === false) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setIsError(false);
    setIsOfflineData(false);
    try {
      if (isOnline) {
        const result = await queryFn();
        setData(result);
        await offlineCache.add({
          query: { key: queryKey, ...stableQueryParams },
          results: Array.isArray(result) ? result : [result],
          resultCount: Array.isArray(result) ? result.length : 1,
        });
      } else {
        const cached = await offlineCache.findByQuery({ key: queryKey, ...stableQueryParams });
        if (cached) {
          setData(cached.results as T);
          setIsOfflineData(true);
        } else {
          throw new Error("Sin conexión y no hay datos en cache.");
        }
      }
    } catch (err) {
      setIsError(true);
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, [isOnline, queryFn, queryKey, stableQueryParams, options?.enabled]);

  useEffect(() => {
    const timer = setTimeout(() => {
      void execute();
    }, 0);
    return () => clearTimeout(timer);
  }, [execute]);

  return { data, isLoading, isError, isOfflineData, error, refetch: execute };
}

export function OfflineBanner() {
  const { isOnline, connectionType } = useNetworkStatus();
  if (isOnline) return null;
  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-amber-500 text-white px-4 py-2 text-center text-sm font-medium">
      <span className="inline-flex items-center gap-2">
        <svg
          className="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"
          />
        </svg>
        Sin conexión a internet{" "}
        {connectionType !== "none" && <span className="text-amber-100">· Mostrando datos en cache</span>}
      </span>
    </div>
  );
}
