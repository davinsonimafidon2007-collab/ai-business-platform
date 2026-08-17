import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useHydrated } from "@/app/hooks/use-hydrated";

describe("useHydrated", () => {
  it("returns true after the component hydrates on the client", async () => {
    const { result } = renderHook(() => useHydrated());
    await waitFor(() => expect(result.current).toBe(true));
  });

  it("keeps returning true across re-renders (stable)", async () => {
    const { result, rerender } = renderHook(() => useHydrated());
    await waitFor(() => expect(result.current).toBe(true));
    rerender();
    expect(result.current).toBe(true);
  });
});
