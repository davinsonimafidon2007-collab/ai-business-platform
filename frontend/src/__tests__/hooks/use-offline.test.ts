import { describe, it, expect, beforeEach } from "vitest";
import {
  offlineCache,
  OFFLINE_CACHE_KEY,
  MAX_ITEMS,
} from "@/app/hooks/use-offline";

const query = { key: "bmw-320d" };
const entry = { query, results: [1, 2], resultCount: 2 };

describe("offlineCache", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("adds a new entry and retrieves it by query", async () => {
    await offlineCache.add(entry);

    const found = await offlineCache.findByQuery(query);
    expect(found).not.toBeNull();
    expect(found?.results).toEqual([1, 2]);
    expect(found?.resultCount).toBe(2);
  });

  it("deduplicates identical queries by updating in place", async () => {
    await offlineCache.add(entry);
    await offlineCache.add({ query, results: [3], resultCount: 1 });

    const all = await offlineCache.getAll();
    expect(all).toHaveLength(1);
    expect(all[0].results).toEqual([3]);
  });

  it("caps the number of stored entries at MAX_ITEMS", async () => {
    for (let i = 0; i < MAX_ITEMS + 5; i++) {
      await offlineCache.add({
        query: { key: `q-${i}` },
        results: [],
        resultCount: 0,
      });
    }

    const all = await offlineCache.getAll();
    expect(all.length).toBeLessThanOrEqual(MAX_ITEMS);
  });

  it("removes an entry by query", async () => {
    await offlineCache.add(entry);
    await offlineCache.remove(query);

    expect(await offlineCache.findByQuery(query)).toBeNull();
  });

  it("clears every stored entry", async () => {
    await offlineCache.add(entry);
    await offlineCache.clear();

    expect(await offlineCache.getAll()).toHaveLength(0);
    expect(window.localStorage.getItem(OFFLINE_CACHE_KEY)).toBeNull();
  });

  it("returns an empty list when the stored cache is corrupt", async () => {
    window.localStorage.setItem(OFFLINE_CACHE_KEY, "{not json");
    expect(await offlineCache.getAll()).toHaveLength(0);
  });
});
