import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCachedQuery, resetSnapshotCache } from "@/app/hooks/use-cached-query";
import { cacheKey, cacheSet } from "@/app/services/api/storage-cache";

const QUERY = "cached-query:test";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = "QueryClientWrapper";
  return { Wrapper, queryClient };
}

// Escribe una entrada en localStorage envejecida/stale a propÃ³sito.
function seedStaleCache(value: unknown, ttlMs = 100) {
  cacheSet(QUERY, value);
  const entry = JSON.parse(window.localStorage.getItem(cacheKey(QUERY))!);
  entry.storedAt = Date.now() - ttlMs - 1000;
  window.localStorage.setItem(cacheKey(QUERY), JSON.stringify(entry));
}

describe("useCachedQuery", () => {
  beforeEach(() => {
    resetSnapshotCache();
  });

  afterEach(() => {
    window.localStorage.clear();
    resetSnapshotCache();
  });

  it("serves cached data immediately and does not fetch when fresh", async () => {
    cacheSet(QUERY, { items: [1] });
    const fetcher = vi.fn().mockResolvedValue({ items: [2] });

    const { Wrapper } = createWrapper();
    const { result } = renderHook(
      () =>
        useCachedQuery<{ items: number[] }>({
          cacheName: QUERY,
          queryFn: fetcher,
        }),
      { wrapper: Wrapper },
    );

    await waitFor(() => expect(result.current.data).toEqual({ items: [1] }));
    // fresh: staleTime=TTL, asÃ­ que el queryFn no deberÃ­a dispararse
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("persists fresh data into localStorage after fetch", async () => {
    const fetcher = vi.fn().mockResolvedValue({ items: [9] });
    const { Wrapper } = createWrapper();
    const { result } = renderHook(
      () =>
        useCachedQuery<{ items: number[] }>({
          cacheName: QUERY,
          queryFn: fetcher,
        }),
      { wrapper: Wrapper },
    );

    await waitFor(() => expect(result.current.data).toEqual({ items: [9] }));
    const stored = JSON.parse(window.localStorage.getItem(cacheKey(QUERY))!);
    expect(stored.value).toEqual({ items: [9] });
  });

  it("revalidates in background when cached entry is expired", async () => {
    seedStaleCache({ items: [1] });
    const fetcher = vi.fn().mockResolvedValue({ items: [2] });

    const { Wrapper } = createWrapper();
    const { result } = renderHook(
      () =>
        useCachedQuery<{ items: number[] }>({
          cacheName: QUERY,
          ttlMs: 100,
          queryFn: fetcher,
        }),
      { wrapper: Wrapper },
    );

    // placeholder (stale) se sirve de inmediato, luego el refresh en segundo
    // plano reemplaza por datos frescos.
    await waitFor(() => expect(result.current.data).toEqual({ items: [2] }));
    // El queryFn debe haberse ejecutado (para refrescar)...
    expect(fetcher).toHaveBeenCalled();
  });

  it("flags isBackgroundRefreshing while an expired cache is being refreshed", async () => {
    seedStaleCache({ items: [1] });
    let resolveFetch: (v: { items: number[] }) => void;
    const fetcher = vi
      .fn()
      .mockImplementation(
        () => new Promise<{ items: number[] }>((resolve) => { resolveFetch = resolve; }),
      );

    const { Wrapper } = createWrapper();

    type HookResult = ReturnType<
      typeof useCachedQuery<{ items: number[] }>
    >;
    let result: { current: HookResult } | undefined;
    act(() => {
      const rendered = renderHook(
        () =>
          useCachedQuery<{ items: number[] }>({
            cacheName: QUERY,
            ttlMs: 100,
            queryFn: fetcher,
          }),
        { wrapper: Wrapper },
      );
      result = rendered.result;
    });

    // placeholder data is served -> stale value shown immediately
    await waitFor(() => expect(result!.current.data).toEqual({ items: [1] }));

    // background refresh in flight -> flag on
    await waitFor(() => expect(result!.current.isBackgroundRefreshing).toBe(true));

    await act(async () => {
      resolveFetch!({ items: [2] });
    });

    await waitFor(() => expect(result!.current.isBackgroundRefreshing).toBe(false));
  });
});