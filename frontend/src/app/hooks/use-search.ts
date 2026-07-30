import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { searchService } from "@/app/services/search";
import type {
  DashboardStats,
  SearchAPIRequest,
  SearchAPIResponse,
  SearchFilters,
  SearchHistory,
} from "@/app/types/vehicle";

export function useSearchVehicles() {
  const queryClient = useQueryClient();

  return useMutation<SearchAPIResponse, Error, SearchAPIRequest>({
    mutationFn: (params: SearchAPIRequest) =>
      searchService.searchVehicles(params),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["searchResults"], data);
      // Save search to history (fire and forget, don't block the UI)
      searchService.saveSearchToHistory({
        query: variables.query,
        results_count: data.summary.total_results,
        execution_time: 0, // Will be calculated by backend if needed
        providers_used: variables.providers,
      }).catch(() => {
        // Silently fail - history is not critical
      });
    },
  });
}

export function useSearchResults() {
  return useQuery<SearchAPIResponse | null>({
    queryKey: ["searchResults"],
    enabled: false,
  });
}

export function useSearchHistory() {
  return useQuery<SearchHistory[]>({
    queryKey: ["searchHistory"],
    queryFn: () => searchService.getSearchHistory(),
  });
}

export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: ["dashboardStats"],
    queryFn: () => searchService.getDashboardStats(),
  });
}

export function useDeleteSearch() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (id: string) => searchService.deleteSearch(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["searchHistory"] });
    },
  });
}

export function formatFiltersForApi(filters: SearchFilters): SearchAPIRequest {
  return {
    query: filters.query || filters.brand || "*",
    providers: filters.provider ? [filters.provider] : undefined,
    max_results: 30,
    min_price: filters.min_price || undefined,
    max_price: filters.max_price || undefined,
    brand: filters.brand || undefined,
    model: filters.model || undefined,
    min_year: filters.min_year || undefined,
    max_year: filters.max_year || undefined,
    min_mileage: filters.min_mileage || undefined,
    max_mileage: filters.max_mileage || undefined,
    fuel_type: filters.fuel_type || undefined,
    transmission: filters.transmission || undefined,
  };
}
