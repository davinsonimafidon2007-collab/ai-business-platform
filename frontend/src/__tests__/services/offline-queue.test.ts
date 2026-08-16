import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";

import {
  queueAction,
  getPendingActions,
  removePendingAction,
  syncPendingActions,
  isOnline,
} from "@/app/services/offline-queue";

// jsdom no implementa IndexedDB: usamos un fake mínimo (un único objectStore)
// suficiente para las operaciones de offline-queue. Los requests resuelven de
// forma síncrona al asignar el handler (equivalente a un IDB immediate).
class FakeIDBObjectStore {
  rows: Array<Record<string, unknown>> = [];

  private nextId(): number {
    return this.rows.reduce((max, r) => Math.max(max, Number(r.id)), 0) + 1;
  }

  add(value: Record<string, unknown>) {
    const store = this;
    const id = this.nextId();
    this.rows.push({ ...value, id });
    return {
      get result() {
        return id;
      },
      set onsuccess(fn: () => void) {
        fn();
      },
      set onerror(_fn: () => void) {
        // success path only in this fake
      },
    };
  }

  getAll() {
    const store = this;
    return {
      get result() {
        return [...store.rows];
      },
      set onsuccess(fn: () => void) {
        fn();
      },
      set onerror(_fn: () => void) {
        // success path only in this fake
      },
    };
  }

  delete(id: number) {
    const store = this;
    this.rows = this.rows.filter((r) => Number(r.id) !== id);
    return {
      get result() {
        return undefined;
      },
      set onsuccess(fn: () => void) {
        fn();
      },
      set onerror(_fn: () => void) {
        // success path only in this fake
      },
    };
  }
}

function installFakeIndexedDB(): FakeIDBObjectStore {
  const store = new FakeIDBObjectStore();
  const db = {
    objectStoreNames: { contains: () => true },
    createObjectStore: () => store,
    transaction: () => ({
      objectStore: () => store,
    }),
  };
  const openRequest = {
    result: db,
    onupgradeneeded: null as unknown as (ev: { target: { result: unknown } }) => void,
    onsuccess: null as unknown as (ev: { target: { result: unknown } }) => void,
    onerror: null as unknown as () => void,
  };
  const fakeIndexedDB = {
    open: () => {
      // Simula la apertura asíncrona de la DB con los eventos de IDBOpenDBRequest.
      Promise.resolve().then(() => {
        openRequest.onupgradeneeded?.({ target: { result: db } });
        openRequest.onsuccess?.({ target: { result: db } });
      });
      return openRequest;
    },
  } as unknown as IDBFactory;
  (globalThis as Record<string, unknown>).indexedDB = fakeIndexedDB;
  return store;
}

describe("offline-queue", () => {
  let store: FakeIDBObjectStore;

  beforeEach(() => {
    store = installFakeIndexedDB();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("isOnline mirrors navigator.onLine", () => {
    Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
    expect(isOnline()).toBe(true);
    Object.defineProperty(navigator, "onLine", { value: false, configurable: true });
    expect(isOnline()).toBe(false);
  });

  it("queues an action and reads it back", async () => {
    await queueAction({
      url: "/api/v1/vehicles/abc/favorite",
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: { vehicle_id: "abc" },
    });

    const pending = await getPendingActions();
    expect(pending).toHaveLength(1);
    expect(pending[0].url).toContain("/favorite");
    expect(pending[0].method).toBe("POST");
    expect(pending[0].timestamp).toBeGreaterThan(0);
  });

  it("removes a single pending action", async () => {
    await queueAction({
      url: "/api/v1/vehicles/a/favorite",
      method: "POST",
      headers: {},
      body: { vehicle_id: "a" },
    });
    await queueAction({
      url: "/api/v1/vehicles/b/favorite",
      method: "POST",
      headers: {},
      body: { vehicle_id: "b" },
    });

    const pending = await getPendingActions();
    await removePendingAction(pending[0].id!);

    const after = await getPendingActions();
    expect(after).toHaveLength(1);
    expect(after[0].body).toEqual({ vehicle_id: "b" });
  });

  it("syncs successful actions and removes them from the queue", async () => {
    await queueAction({
      url: "/api/v1/vehicles/abc/favorite",
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: { vehicle_id: "abc" },
    });

    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);

    const result = await syncPendingActions();

    expect(result).toEqual({ success: 1, failed: 0 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(await getPendingActions()).toHaveLength(0);
  });

  it("keeps actions in the queue when sync fails", async () => {
    await queueAction({
      url: "/api/v1/vehicles/abc/favorite",
      method: "POST",
      headers: {},
      body: { vehicle_id: "abc" },
    });

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    const result = await syncPendingActions();

    expect(result).toEqual({ success: 0, failed: 1 });
    expect(await getPendingActions()).toHaveLength(1);
  });
});
