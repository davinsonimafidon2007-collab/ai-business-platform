import { api } from "./api/client";
import type {
  SearchAPIRequest,
  SearchAPIResponse,
  SearchHistory,
} from "@/app/types/vehicle";
import type { DashboardStats } from "@/app/types/search-orders";

export const searchService = {
  async searchVehicles(
    params: SearchAPIRequest
  ): Promise<SearchAPIResponse> {
    const { data } = await api.post<SearchAPIResponse>("/search", params);
    return data;
  },

  async getSearchHistory(): Promise<SearchHistory[]> {
    const { data } = await api.get<SearchHistory[]>("/searches");
    return data;
  },

  async getSearchById(id: string): Promise<SearchHistory> {
    const { data } = await api.get<SearchHistory>(`/searches/${id}`);
    return data;
  },

  async deleteSearch(id: string): Promise<void> {
    await api.delete(`/searches/${id}`);
  },

  async saveSearchToHistory(searchData: {
    query: string;
    results_count: number;
    execution_time: number;
    providers_used?: string[];
  }): Promise<SearchHistory> {
    const payload = {
      name: `Search: ${searchData.query}`,
      country: "ES",
      brands: null,
      models: null,
      filters: JSON.stringify({
        query: searchData.query,
        providers: searchData.providers_used,
      }),
      query: searchData.query,
      results_count: searchData.results_count,
      execution_time: searchData.execution_time,
    };
    const { data: result } = await api.post<SearchHistory>("/searches", payload);
    return result;
  },

  async getDashboardStats(): Promise<DashboardStats> {
    const { data } = await api.get("/dashboard/stats");
    return data;
  },
};