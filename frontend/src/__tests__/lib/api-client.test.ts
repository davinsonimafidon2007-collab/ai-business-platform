import { describe, test, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchWithRetry } from "@/lib/api-client";

describe("fetchWithRetry", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.useRealTimers();
  });

  test("succeeds on first attempt", async () => {
    const mockResponse = new Response(JSON.stringify({ ok: true }), { status: 200 });
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    const promise = fetchWithRetry("https://api.example.com/data");
    await vi.runAllTimersAsync();
    const res = await promise;

    expect(res.status).toBe(200);
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  test("retries on 500 error and eventually succeeds", async () => {
    const errorResponse = new Response("Server Error", { status: 500 });
    const successResponse = new Response("OK", { status: 200 });

    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(errorResponse)
      .mockResolvedValueOnce(successResponse);

    const promise = fetchWithRetry("https://api.example.com/data", {}, 2, 100);
    await vi.runAllTimersAsync();
    const res = await promise;

    expect(res.status).toBe(200);
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  test("retries on TypeError network error and returns error after exhausting retries", async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));

    const promise = fetchWithRetry("https://api.example.com/data", {}, 2, 100);

    const catchPromise = expect(promise).rejects.toThrow("Failed to fetch");

    await vi.runAllTimersAsync();
    await catchPromise;

    expect(global.fetch).toHaveBeenCalledTimes(3);
  });
});
