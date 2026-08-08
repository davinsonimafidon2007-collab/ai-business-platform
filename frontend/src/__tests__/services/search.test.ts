import { describe, it, expect, vi, beforeEach } from "vitest";

// Solo se mockea el cliente HTTP: aquí se prueba searchService de verdad.
// `use-search.test.tsx` mockea el módulo entero, así que se desmockea
// explícitamente para no heredar su doble entre ficheros.
vi.unmock("@/app/services/search");
vi.mock("@/app/services/api/client", () => ({
  api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

import { api } from "@/app/services/api/client";
import { searchService } from "@/app/services/search";

describe("searchService", () => {
  beforeEach(() => vi.clearAllMocks());

  it("posts the search request and returns the body", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { summary: { total_results: 2 }, results: [{}, {}] },
    });

    const result = await searchService.searchVehicles({
      query: "BMW",
      max_results: 5,
    } as never);

    expect(api.post).toHaveBeenCalledWith("/search", {
      query: "BMW",
      max_results: 5,
    });
    expect(result.summary.total_results).toBe(2);
  });

  it("gets the search history", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [{ id: "s1" }] });

    const history = await searchService.getSearchHistory();

    expect(api.get).toHaveBeenCalledWith("/searches");
    expect(history).toHaveLength(1);
  });

  it("gets a single search by id", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { id: "s1" } });

    const search = await searchService.getSearchById("s1");

    expect(api.get).toHaveBeenCalledWith("/searches/s1");
    expect(search.id).toBe("s1");
  });

  it("deletes a search", async () => {
    vi.mocked(api.delete).mockResolvedValue({ data: undefined });

    await searchService.deleteSearch("s1");

    expect(api.delete).toHaveBeenCalledWith("/searches/s1");
  });

  it("builds the payload when saving to history", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { id: "s9" } });

    await searchService.saveSearchToHistory({
      query: "Audi A4",
      results_count: 7,
      execution_time: 1.5,
      providers_used: ["autoscout24"],
    });

    const [url, payload] = vi.mocked(api.post).mock.calls[0];
    expect(url).toBe("/searches");
    expect(payload).toMatchObject({
      name: "Search: Audi A4",
      country: "ES",
      query: "Audi A4",
      results_count: 7,
      execution_time: 1.5,
    });
    // `filters` viaja serializado: si deja de ser string, el backend lo rechaza.
    expect(JSON.parse((payload as { filters: string }).filters)).toEqual({
      query: "Audi A4",
      providers: ["autoscout24"],
    });
  });

  it("gets dashboard stats", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { total_searches: 3 } });

    const stats = await searchService.getDashboardStats();

    expect(api.get).toHaveBeenCalledWith("/dashboard/stats");
    expect(stats.total_searches).toBe(3);
  });
});
