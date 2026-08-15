/**
 * Service Worker for offline support — TASK-016 (FASE 5).
 *
 * Caches API responses (vehicles, opportunities, deals, searches) and serves
 * them when offline. Queues mutations (favorites, etc.) for later sync via
 * IndexedDB — consumed by `offline-queue.ts` / `syncPendingActions`.
 *
 * Next.js export: `public/` → `out/`, registrado como `/service-worker.js`.
 */

const CACHE_NAME = "abp-cache-v1";
const API_CACHE_PATTERN = /\/api\/v1\/(vehicles|opportunities|deals|searches|dashboard)/;
const STATIC_ASSETS = [
  "/",
  "/dashboard/",
  "/opportunities/",
  "/search/",
];

// Install: precache rutas estáticas.
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS).catch(() => {}))
  );
  self.skipWaiting();
});

// Activate: limpiar caches viejas.
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) =>
        Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_NAME)
            .map((name) => caches.delete(name))
        )
      )
  );
  self.clients.claim();
});

// Fetch: cache API GET, stale-while-revalidate. Fallback 503 offline sin cache.
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== "GET") {
    // Las mutaciones las encola el cliente (offline-queue) cuando está
    // offline; aquí solo se cachean GETs.
    return;
  }

  // Solo rutas de la misma app (no CDNs/API externas).
  if (API_CACHE_PATTERN.test(url.pathname)) {
    event.respondWith(
      caches.match(request).then((cached) => {
        const networkFetch = fetch(request)
          .then((response) => {
            if (response && response.ok) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
            }
            return response;
          })
          .catch(() => null);

        if (cached) {
          // Devolver cache y refrescar en background (stale-while-revalidate).
          networkFetch;
          return cached;
        }
        return networkFetch.then((response) => {
          if (response) return response;
          return new Response(
            JSON.stringify({ error: "Offline and no cached data available" }),
            { status: 503, headers: { "Content-Type": "application/json" } }
          );
        });
      })
    );
    return;
  }

  // Assets estáticos (JS/CSS/imágenes): network-first con fallback a cache.
  event.respondWith(
    caches.match(request).then((cached) => {
      const networkFetch = fetch(request).catch(() => null);
      return networkFetch.then((response) => response || cached);
    })
  );
});

// Background sync: cola de favoritos (opcional en web; el cliente usa IndexedDB).
self.addEventListener("sync", (event) => {
  if (event.tag === "sync-favorites") {
    event.waitUntil(syncFromIndexedDB());
  }
});

async function syncFromIndexedDB() {
  const db = await openIndexedDB();
  const tx = db.transaction("pendingActions", "readonly");
  const store = tx.objectStore("pendingActions");
  const actions = await new Promise((resolve, reject) => {
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });

  for (const action of actions) {
    try {
      const response = await fetch(action.url, {
        method: action.method,
        headers: action.headers,
        body: action.body ? JSON.stringify(action.body) : undefined,
      });
      if (response.ok) {
        const deleteTx = db.transaction("pendingActions", "readwrite");
        await new Promise((resolve, reject) => {
          const req = deleteTx.objectStore("pendingActions").delete(action.id);
          req.onsuccess = () => resolve();
          req.onerror = () => reject(req.error);
        });
      }
    } catch (err) {
      console.error("Sync failed for action:", action.id, err);
    }
  }
}

function openIndexedDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("abp-offline-db", 1);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains("pendingActions")) {
        db.createObjectStore("pendingActions", { keyPath: "id", autoIncrement: true });
      }
    };
  });
}
