import { useCallback, useSyncExternalStore } from "react";
import { useQuery, UseQueryOptions, UseQueryResult, QueryFunction } from "@tanstack/react-query";
import {
  cacheGet,
  cacheIsExpired,
  cacheSet,
  subscribeToCacheChanges,
  DEFAULT_TTL_MS,
} from "@/app/services/api/storage-cache";

// useSyncExternalStore exige un snapshot estable por referencia. cacheGet
// deserializa un objeto nuevo en cada llamada, así que guardamos el último
// snapshot por cacheName aquí. El listener de cambios lo invalida para que
// la siguiente lectura refleje localStorage de nuevo.
const snapshotCache = new Map<string, { value: unknown }>();

function readSnapshot<T>(name: string, staleWhileRevalidate: boolean): T | null {
  if (!staleWhileRevalidate) return null;
  const cached = snapshotCache.get(name);
  if (cached) return cached.value as T | null;
  const value = cacheGet<T>(name);
  snapshotCache.set(name, { value });
  return value;
}

function invalidateSnapshot(name: string): void {
  snapshotCache.delete(name);
}

/**
 * Vacía el snapshot cache interno. Se usa en tests (SSR-safe) para que las
 * entradas escritas a mano en localStorage se lean de nuevo.
 */
export function resetSnapshotCache(): void {
  snapshotCache.clear();
}

export interface UseCachedQueryOptions<T, E> {
  cacheName: string;
  ttlMs?: number;
  staleWhileRevalidate?: boolean;
  queryFn: QueryFunction<T>;
  queryKey?: unknown[];
  queryOptions?: Omit<UseQueryOptions<T, E, T>, "queryKey" | "queryFn" | "initialData" | "placeholderData" | "staleTime">;
}

/**
 * useQuery con caché opt-in en localStorage (stale-while-revalidate).
 *
 * - Datos frescos (TTL no superado): se sirven desde localStorage con
 *   `initialData` y `staleTime`, de modo que el queryFn NO se dispara.
 * - Datos caducados: se sirven como placeholder mientras el queryFn refresca
 *   en segundo plano (`isBackgroundRefreshing` = true).
 * - Sin caché: fetch normal; el resultado se persiste en localStorage.
 *
 * El snapshot de localStorage se lee con useSyncExternalStore (SSR-safe):
 * devuelve null durante SSR y el valor real tras la hidratación, disparando
 * un re-render sin setState en effects.
 */
export function useCachedQuery<T, E = Error>({
  cacheName,
  ttlMs = DEFAULT_TTL_MS,
  staleWhileRevalidate = true,
  queryFn,
  queryKey,
  queryOptions = {},
}: UseCachedQueryOptions<T, E>): UseQueryResult<T, E> & {
  isBackgroundRefreshing: boolean;
} {
  const subscribe = useCallback(
    (onChange: () => void) => {
      return subscribeToCacheChanges(() => {
        invalidateSnapshot(cacheName);
        onChange();
      });
    },
    [cacheName]
  );
  const getSnapshot = useCallback(
    () => readSnapshot<T>(cacheName, staleWhileRevalidate),
    [cacheName, staleWhileRevalidate]
  );
  const getServerSnapshot = useCallback(() => null, []);

  const cachedData = useSyncExternalStore<T | null>(
    subscribe,
    getSnapshot,
    getServerSnapshot
  );
  const expired = staleWhileRevalidate
    ? cacheIsExpired<T>(cacheName, ttlMs)
    : true;

  // Narrowing explícito: tras comprobar `!== null`, TS no propaga la exclusión
  // de null a través de las constantes booleanas, así que lo forzamos aquí.
  const cachedValue: T | null = cachedData;
  const freshAndCached = staleWhileRevalidate && cachedValue !== null && !expired;
  const staleAndCached = staleWhileRevalidate && cachedValue !== null && expired;

  const result = useQuery<T, E>({
    ...queryOptions,
    queryKey: queryKey ?? [cacheName],
    queryFn: async (context) => {
      const fresh = await queryFn(context);
      if (typeof fresh !== "undefined" && fresh !== null) {
        cacheSet(cacheName, fresh);
        invalidateSnapshot(cacheName);
      }
      return fresh;
    },
    // initialData en ambos casos: para datos frescos evita el fetch; para
    // datos caducos muestra la versión stale de inmediato y, como staleTime=0,
    // React Query refetcha en segundo plano sin bloquear la UI.
    initialData: staleWhileRevalidate && cachedValue !== null ? (cachedValue as T) : undefined,
    staleTime: freshAndCached ? ttlMs : 0,
  });

  return {
    ...result,
    isBackgroundRefreshing: staleAndCached && result.isFetching,
  };
}