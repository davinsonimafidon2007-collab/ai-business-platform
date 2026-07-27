import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { searchService } from "@/app/services/search";
import type {
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
    onSuccess: (data) => {
      queryClient.setQueryData(["searchResults"], data);
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
  const parts: string[] = [];

  if (filters.query) parts.push(filters.query);
  if (filters.brand) parts.push(filters.brand);
  if (filters.model) parts.push(filters.model);
  if (filters.min_year)
    parts.push(`year_from:${filters.min_year}`);
  if (filters.max_year)
    parts.push(`year_to:${filters.max_year}`);
  if (filters.min_mileage)
    parts.push(`mileage_from:${filters.min_mileage}`);
  if (filters.max_mileage)
    parts.push(`mileage_to:${filters.max_mileage}`);
  if (filters.fuel_type)
    parts.push(`fuel:${filters.fuel_type}`);
  if (filters.transmission)
    parts.push(`transmission:${filters.transmission}`);
  if (filters.min_price)
    parts.push(`min_price:${filters.min_price}`);
  if (filters.max_price)
    parts.push(`max_price:${filters.max_price}`);

  const query = parts.join(" ");

  return {
    query: query || filters.query || "*",
    providers: filters.provider ? [filters.provider] : undefined,
    max_results: 30,
    min_price: filters.min_price || undefined,
    max_price: filters.max_price || undefined,
  };
}