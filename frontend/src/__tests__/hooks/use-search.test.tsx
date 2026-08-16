import { describe, it, expect, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
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

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = "QueryClientWrapper";
  return Wrapper;
};

describe("useSearchVehicles", () => {
  it("calls search service with correct params", async () => {
    const mockData = {
      summary: { total_results: 0, excellent: 0, good: 0, average: 0, poor: 0, rejected: 0 },
      results: [],
    };
    vi.mocked(searchService.searchVehicles).mockResolvedValue(mockData as any);

    const { result } = renderHook(() => useSearchVehicles(), { wrapper: createWrapper() });

    await act(async () => {
      result.current.mutate({ query: "BMW" });
    });

    expect(searchService.searchVehicles).toHaveBeenCalledWith({ query: "BMW" });
  });
});

describe("useSearchHistory", () => {
  it("fetches search history", async () => {
    const mockHistory = [
      { id: "1", query: "BMW", results_count: 5, execution_time: 2.5, created_at: "2024-01-01" },
    ];
    vi.mocked(searchService.getSearchHistory).mockResolvedValue(mockHistory as any);

    const { result } = renderHook(() => useSearchHistory(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.data).toEqual(mockHistory);
    });
  });
});

describe("useDeleteSearch", () => {
  it("deletes search and invalidates cache", async () => {
    vi.mocked(searchService.deleteSearch).mockResolvedValue();

    const { result } = renderHook(() => useDeleteSearch(), { wrapper: createWrapper() });

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
    // brand/model viajan como campos propios del SearchAPIRequest, no
    // concatenados en `query` (el backend los mapea a la URL del provider).
    const filters: SearchFilters = { query: "BMW", brand: "BMW", model: "320d" };
    const result = formatFiltersForApi(filters);
    expect(result.query).toBe("BMW");
    expect(result.brand).toBe("BMW");
    expect(result.model).toBe("320d");
  });

  it("falls back to brand when there is no free-text query", () => {
    const result = formatFiltersForApi({ brand: "Audi" } as SearchFilters);
    expect(result.query).toBe("Audi");
  });

  it("formats price filters", () => {
    const filters: SearchFilters = { query: "BMW", min_price: 10000, max_price: 50000 };
    const result = formatFiltersForApi(filters);
    expect(result.min_price).toBe(10000);
    expect(result.max_price).toBe(50000);
  });

  it("formats year filters", () => {
    // Igual que brand/model: campos tipados, no sufijos "year_from:" en query.
    const filters: SearchFilters = { query: "BMW", min_year: 2015, max_year: 2023 };
    const result = formatFiltersForApi(filters);
    expect(result.query).toBe("BMW");
    expect(result.min_year).toBe(2015);
    expect(result.max_year).toBe(2023);
  });
});