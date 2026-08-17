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

  /**
   * Obtiene la lista estática de marcas y modelos con caché local L3 (LocalStorage) (TASK-018).
   *
   * Si está guardada en LocalStorage y no ha expirado (24h), la devuelve de forma inmediata,
   * reduciendo el consumo de red en redes móviles/Capacitor.
   */
  async getStaticBrandsAndModels(): Promise<Record<string, string[]>> {
    const CACHE_KEY = "static_brands_models_v1";
    const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 horas

    if (typeof window !== "undefined") {
      try {
        const cached = localStorage.getItem(CACHE_KEY);
        if (cached) {
          const { data, timestamp } = JSON.parse(cached);
          if (Date.now() - timestamp < CACHE_TTL) {
            return data;
          }
        }
      } catch (e) {
        console.warn("Failed to read from LocalStorage cache", e);
      }
    }

    // Listado estático de apoyo por defecto (versión 2026)
    const data: Record<string, string[]> = {
      Audi: ["A1", "A3", "A4", "A5", "A6", "Q3", "Q5", "TT"],
      BMW: ["Serie 1", "Serie 2", "Serie 3", "Serie 4", "Serie 5", "X1", "X3", "X5"],
      Mercedes: ["Clase A", "Clase B", "Clase C", "Clase E", "CLA", "GLA", "GLC"],
      Volkswagen: ["Golf", "Polo", "Passat", "Tiguan", "T-Roc", "Scirocco"],
      Seat: ["Ibiza", "Leon", "Arona", "Ateca"],
    };

    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(
          CACHE_KEY,
          JSON.stringify({ data, timestamp: Date.now() })
        );
      } catch (e) {
        console.warn("Failed to write to LocalStorage cache", e);
      }
    }

    return data;
  },
};