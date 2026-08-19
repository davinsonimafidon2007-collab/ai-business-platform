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
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

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
    expect(JSON.parse((payload as { filters: string }).filters)).toEqual({
      query: "Audi A4",
      providers: ["autoscout24"],
    });
  });

  it("saves search to history without providers_used", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { id: "s10" } });
    await searchService.saveSearchToHistory({
      query: "Seat Leon",
      results_count: 5,
      execution_time: 1.0,
    });
    expect(api.post).toHaveBeenCalled();
  });

  it("gets dashboard stats", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { total_searches: 3 } });

    const stats = await searchService.getDashboardStats();

    expect(api.get).toHaveBeenCalledWith("/dashboard/stats");
    expect(stats.total_searches).toBe(3);
  });

  it("gets static brands and models from cache and fallback", async () => {
    const data = await searchService.getStaticBrandsAndModels();
    expect(data.BMW).toContain("Serie 3");

    // Next call reads from LocalStorage
    const cachedData = await searchService.getStaticBrandsAndModels();
    expect(cachedData.Audi).toContain("A4");
  });

  it("handles empty or invalid LocalStorage in getStaticBrandsAndModels", async () => {
    localStorage.setItem("static_brands_models_v1", "invalid json");
    const data = await searchService.getStaticBrandsAndModels();
    expect(data.BMW).toBeDefined();
  });

  it("handles expired cache in getStaticBrandsAndModels", async () => {
    const expiredTime = Date.now() - 48 * 60 * 60 * 1000;
    localStorage.setItem(
      "static_brands_models_v1",
      JSON.stringify({ data: { Tesla: ["Model 3"] }, timestamp: expiredTime })
    );
    const data = await searchService.getStaticBrandsAndModels();
    expect(data.Audi).toBeDefined();
  });
});
