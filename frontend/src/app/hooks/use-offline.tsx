"use client";

/**
 * MOB-P1-008: Offline Service
 * Cache de busqueda y deteccion de red en tiempo real.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { Capacitor } from "@capacitor/core";

export const OFFLINE_CACHE_KEY = "abp_offline_cache";
export const MAX_ITEMS = 20;

export interface OfflineQuery {
  key: string;
  [key: string]: unknown;
}

export interface CachedSearch {
  id: string;
  query: OfflineQuery;
  results: unknown[];
  resultCount: number;
  cachedAt: number;
}

export interface OfflineState {
  isOnline: boolean;
  connectionType: string;
}

function readAll(): CachedSearch[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(OFFLINE_CACHE_KEY);
    return raw ? (JSON.parse(raw) as CachedSearch[]) : [];
  } catch {
    return [];
  }
}

function writeAll(entries: CachedSearch[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(OFFLINE_CACHE_KEY, JSON.stringify(entries));
}

function sameQuery(a: OfflineQuery, b: OfflineQuery): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export const offlineCache = {
  async getAll(): Promise<CachedSearch[]> {
    return readAll();
  },
  async add(search: Omit<CachedSearch, "id" | "cachedAt">): Promise<void> {
    const cached = readAll();
    const newEntry: CachedSearch = {
      ...search,
      id: "search_" + Date.now() + "_" + Math.random().toString(36).substring(2, 11),
      cachedAt: Date.now(),
    };
    const deduped = cached.filter((c) => !sameQuery(c.query, search.query));
    writeAll([newEntry, ...deduped].slice(0, MAX_ITEMS));
  },
  async findByQuery(query: OfflineQuery): Promise<CachedSearch | null> {
    return readAll().find((c) => sameQuery(c.query, query)) || null;
  },
  async remove(query: OfflineQuery): Promise<void> {
    writeAll(readAll().filter((c) => !sameQuery(c.query, query)));
  },
  async clear(): Promise<void> {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(OFFLINE_CACHE_KEY);
    }
  },
  async getRecent(limit = 5): Promise<CachedSearch[]> {
    return readAll().slice(0, limit);
  },
};

/**
 * Estado de red en tiempo real. En nativo usa @capacitor/network; en web
 * usa navigator.onLine.
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

export function useOfflineSearch<T>(
  queryFn: () => Promise<T>,
  queryKey: string,
  queryParams: OfflineQuery,
  options?: { enabled?: boolean }
) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [isOfflineData, setIsOfflineData] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const { isOnline } = useNetworkStatus();
  const queryParamsKey = JSON.stringify(queryParams);
  const stableQueryParams = useMemo(() => JSON.parse(queryParamsKey) as OfflineQuery, [queryParamsKey]);

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
          query: { ...stableQueryParams, key: queryKey },
          results: Array.isArray(result) ? result : [result],
          resultCount: Array.isArray(result) ? result.length : 1,
        });
      } else {
        const cached = await offlineCache.findByQuery({ ...stableQueryParams, key: queryKey });
        if (cached) {
          setData(cached.results as T);
          setIsOfflineData(true);
        } else {
          throw new Error("Sin conexion y no hay datos en cache.");
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

export { OfflineBanner } from "@/app/components/offline-banner";
