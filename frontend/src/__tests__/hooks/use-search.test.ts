import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSearchVehicles, useSearchHistory, useDeleteSearch, formatFiltersForApi } from "@/app/hooks/use-search";
import type { SearchFilters } from "@/app/types/vehicle";

// Mock the search service
vi.mock("@/app/services/search", () => ({
  searchService: {
    searchVehicles: vi.fn(),
    getSearchHistory: vi.fn(),
    deleteSearch: vi.fn(),
  },
}));

import { searchService } from "@/app/services/search";

describe("useSearchVehicles", () => {
  it("calls search service with correct params", async () => {
    const mockData = {
      summary: { total_results: 0, excellent: 0, good: 0, average: 0, poor: 0, rejected: 0 },
      results: [],
    };
    vi.mocked(searchService.searchVehicles).mockResolvedValue(mockData as any);

    const { result } = renderHook(() => useSearchVehicles());

    await act(async () => {
      result.current.mutate({ query: "BMW" });
    });

    expect(searchService.searchVehicles).toHaveBeenCalledWith({ query: "BMW" });
    expect(result.current.data).toEqual(mockData);
  });
});

describe("useSearchHistory", () => {
  it("fetches search history", async () => {
    const mockHistory = [
      { id: "1", query: "BMW", results_count: 5, execution_time: 2.5, created_at: "2024-01-01" },
    ];
    vi.mocked(searchService.getSearchHistory).mockResolvedValue(mockHistory as any);

    const { result } = renderHook(() => useSearchHistory());

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(result.current.data).toEqual(mockHistory);
  });
});

describe("useDeleteSearch", () => {
  it("deletes search and invalidates cache", async () => {
    vi.mocked(searchService.deleteSearch).mockResolvedValue();

    const { result } = renderHook(() => useDeleteSearch());

    await act(async () => {
      result.current.mutate("123");
    });

    expect(searchService.deleteSearch).toHaveBeenCalledWith("123");
  });
});

describe("formatFiltersForApi", () => {
  it("formats basic query", () => {
    const filters: SearchFilters = { query: "BMW" };
    const result = formatFiltersForApi(filters);
    expect(result.query).toBe("BMW");
  });

  it("formats filters with brand and model", () => {
    const filters: SearchFilters = { query: "BMW", brand: "BMW", model: "320d" };
    const result = formatFiltersForApi(filters);
    expect(result.query).toBe("BMW BMW 320d");
  });

  it("formats price filters", () => {
    const filters: SearchFilters = { query: "BMW", min_price: 10000, max_price: 50000 };
    const result = formatFiltersForApi(filters);
    expect(result.min_price).toBe(10000);
    expect(result.max_price).toBe(50000);
  });

  it("formats year filters", () => {
    const filters: SearchFilters = { query: "BMW", min_year: 2015, max_year: 2023 };
    const result = formatFiltersForApi(filters);
    expect(result.query).toContain("year_from:2015");
    expect(result.query).toContain("year_to:2023");
  });
});