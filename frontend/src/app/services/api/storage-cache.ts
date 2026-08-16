// Caché opt-in de respuestas de API en localStorage con clave versionada y TTL.
// NO se usa automáticamente: solo servicios que la llamen explícitamente
// (p. ej. datos estáticos como marcas/modelos o market estimates) se benefician.
// Patrón stale-while-revalidate: devuelve lo cacheado si existe, pero refresca
// en segundo plano cuando ha pasado el TTL.
//
// La versión de la clave permite invalidar todas las entradas a la vez cuando
// el contrato de la API cambie (bump `CACHE_VERSION` en lugar de vaciar a mano).

const CACHE_VERSION = "v1";
const CACHE_PREFIX = `api-cache:${CACHE_VERSION}:`;

export const DEFAULT_TTL_MS = 60 * 60 * 1000; // 1h

// Notifica a suscriptores (p. ej. hooks useSyncExternalStore) cuando la caché
// cambia programáticamente. El evento "storage" cubre cambios cross-tab.
const CACHE_CHANGE_EVENT = "api-cache:change";

export function subscribeToCacheChanges(listener: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(CACHE_CHANGE_EVENT, listener);
  window.addEventListener("storage", listener);
  return () => {
    window.removeEventListener(CACHE_CHANGE_EVENT, listener);
    window.removeEventListener("storage", listener);
  };
}

function notifyCacheChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(CACHE_CHANGE_EVENT));
}

interface CacheEntry<T> {
  value: T;
  storedAt: number;
}

function canUseStorage(): boolean {
  return typeof window !== "undefined" && !!window.localStorage;
}

export function cacheKey(name: string): string {
  return `${CACHE_PREFIX}${name}`;
}

export function cacheGet<T>(name: string): T | null {
  if (!canUseStorage()) return null;
  const raw = window.localStorage.getItem(cacheKey(name));
  if (!raw) return null;
  try {
    const entry = JSON.parse(raw) as CacheEntry<T>;
    return entry.value;
  } catch {
    // Entrada corrupta (JSON inválido): se ignora y se trata como miss.
    return null;
  }
}

export function cacheSet<T>(name: string, value: T): void {
  if (!canUseStorage()) return;
  const entry: CacheEntry<T> = { value, storedAt: Date.now() };
  try {
    window.localStorage.setItem(cacheKey(name), JSON.stringify(entry));
  } catch {
    // localStorage lleno o no disponible: el fallo es silencioso, la app sigue
    // funcionando sin caché.
  }
  notifyCacheChanged();
}

export function cacheIsExpired<T>(name: string, ttlMs: number = DEFAULT_TTL_MS): boolean {
  if (!canUseStorage()) return true;
  const raw = window.localStorage.getItem(cacheKey(name));
  if (!raw) return true;
  try {
    const entry = JSON.parse(raw) as CacheEntry<T>;
    return Date.now() - entry.storedAt > ttlMs;
  } catch {
    return true;
  }
}

export function cacheRemove(name: string): void {
  if (!canUseStorage()) return;
  window.localStorage.removeItem(cacheKey(name));
  notifyCacheChanged();
}

export function cacheClearAll(): void {
  if (!canUseStorage()) return;
  const toRemove: string[] = [];
  for (let i = 0; i < window.localStorage.length; i++) {
    const key = window.localStorage.key(i);
    if (key && key.startsWith(CACHE_PREFIX)) {
      toRemove.push(key);
    }
  }
  toRemove.forEach((key) => window.localStorage.removeItem(key));
  notifyCacheChanged();
}
