/**
 * offlineCache — caché offline de búsquedas/resultados.
 *
 * Persiste en localStorage (SSR-safe) un histórico acotado de consultas para
 * poder funcionar sin conexión. Garantiza:
 *   - Deduplicación de consultas idénticas (misma clave JSON).
 *   - Límite máximo de entradas (MAX_ITEMS) descartando las más antiguas.
 */
export interface OfflineQuery {
  key: string;
  [key: string]: unknown;
}

export interface OfflineCacheEntry {
  query: OfflineQuery;
  results: unknown[];
  resultCount: number;
  cachedAt: number;
}

export const OFFLINE_CACHE_KEY = "abp_offline_cache";
export const MAX_ITEMS = 20;

function readAll(): OfflineCacheEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(OFFLINE_CACHE_KEY);
    return raw ? (JSON.parse(raw) as OfflineCacheEntry[]) : [];
  } catch {
    return [];
  }
}

function writeAll(entries: OfflineCacheEntry[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(OFFLINE_CACHE_KEY, JSON.stringify(entries));
}

function sameQuery(a: OfflineQuery, b: OfflineQuery): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export const offlineCache = {
  async add(entry: Omit<OfflineCacheEntry, "cachedAt">): Promise<void> {
    const all = readAll();
    const existing = all.find((e) => sameQuery(e.query, entry.query));
    if (existing) {
      existing.results = entry.results;
      existing.resultCount = entry.resultCount;
      existing.cachedAt = Date.now();
    } else {
      all.unshift({ ...entry, cachedAt: Date.now() });
    }
    writeAll(all.slice(0, MAX_ITEMS));
  },

  async findByQuery(query: OfflineQuery): Promise<OfflineCacheEntry | null> {
    return readAll().find((e) => sameQuery(e.query, query)) ?? null;
  },

  async getAll(): Promise<OfflineCacheEntry[]> {
    return readAll();
  },

  async remove(query: OfflineQuery): Promise<void> {
    writeAll(readAll().filter((e) => !sameQuery(e.query, query)));
  },

  async clear(): Promise<void> {
    if (typeof window !== "undefined") {
      localStorage.removeItem(OFFLINE_CACHE_KEY);
    }
  },
};
