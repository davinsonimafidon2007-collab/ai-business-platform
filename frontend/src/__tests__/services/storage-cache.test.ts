import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  cacheGet,
  cacheSet,
  cacheIsExpired,
  cacheRemove,
  cacheClearAll,
  cacheKey,
  DEFAULT_TTL_MS,
} from "@/app/services/api/storage-cache";

const KEY = "test:vehicles";

describe("storage-cache", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.useRealTimers();
  });

  it("uses a versioned key prefix", () => {
    expect(cacheKey("vehicles")).toBe("api-cache:v1:vehicles");
  });

  it("stores and reads a value round-trip", () => {
    cacheSet(KEY, { total: 5 });
    expect(cacheGet<{ total: number }>(KEY)).toEqual({ total: 5 });
  });

  it("returns null on miss", () => {
    expect(cacheGet(KEY)).toBeNull();
  });

  it("treats corrupted entries as misses", () => {
    window.localStorage.setItem(cacheKey(KEY), "not-json{{{");
    expect(cacheGet(KEY)).toBeNull();
  });

  it("expires entries past TTL", () => {
    vi.useFakeTimers();
    cacheSet(KEY, 123);
    expect(cacheIsExpired<number>(KEY, DEFAULT_TTL_MS)).toBe(false);

    vi.advanceTimersByTime(DEFAULT_TTL_MS + 1);
    expect(cacheIsExpired<number>(KEY, DEFAULT_TTL_MS)).toBe(true);
  });

  it("treats missing/corrupt entries as expired", () => {
    expect(cacheIsExpired(KEY)).toBe(true);
    window.localStorage.setItem(cacheKey(KEY), "nope");
    expect(cacheIsExpired(KEY)).toBe(true);
  });

  it("removes a single key", () => {
    cacheSet(KEY, 1);
    cacheRemove(KEY);
    expect(cacheGet(KEY)).toBeNull();
  });

  it("clears only entries with the api-cache prefix", () => {
    window.localStorage.setItem("unrelated", "keep");
    cacheSet(KEY, 1);
    cacheSet("other", 2);
    cacheClearAll();
    expect(cacheGet(KEY)).toBeNull();
    expect(cacheGet("other")).toBeNull();
    expect(window.localStorage.getItem("unrelated")).toBe("keep");
  });
});
