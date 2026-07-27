import { api } from "./api/client";
import type {
  SearchAPIRequest,
  SearchAPIResponse,
  SearchHistory,
} from "@/app/types/vehicle";

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

  async getDashboardStats(): Promise<{
    total_searches: number;
    total_vehicles: number;
    excellent_opportunities: number;
    average_roi: number;
    average_profit: number;
    recommendation_distribution: Record<string, number>;
  }> {
    const { data } = await api.get("/dashboard/stats");
    return data;
  },
};