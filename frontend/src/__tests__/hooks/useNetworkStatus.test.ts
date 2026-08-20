import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useNetworkStatus, offlineFetch } from "@/hooks/useNetworkStatus";

describe("useNetworkStatus hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns initial online status correctly", () => {
    const { result } = renderHook(() => useNetworkStatus());
    expect(result.current.isOnline).toBe(true);
    expect(result.current.status).toBe("online");
    expect(result.current.connectionType).toBe("wifi");
  });

  it("updates status when window goes offline and online", () => {
    const { result } = renderHook(() => useNetworkStatus());

    act(() => {
      window.dispatchEvent(new Event("offline"));
    });
    expect(result.current.isOnline).toBe(false);
    expect(result.current.status).toBe("offline");
    expect(result.current.connectionType).toBe("none");

    act(() => {
      window.dispatchEvent(new Event("online"));
    });
    expect(result.current.isOnline).toBe(true);
    expect(result.current.status).toBe("online");
  });
});

describe("offlineFetch utility", () => {
  it("returns staleData when offline and staleData is provided", async () => {
    const fetcher = vi.fn();
    const staleData = { data: "cached" };

    const res = await offlineFetch(fetcher, staleData, false);
    expect(res).toEqual(staleData);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("calls fetcher when online", async () => {
    const fetcher = vi.fn().mockResolvedValue({ data: "fresh" });
    const staleData = { data: "cached" };

    const res = await offlineFetch(fetcher, staleData, true);
    expect(res).toEqual({ data: "fresh" });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});
