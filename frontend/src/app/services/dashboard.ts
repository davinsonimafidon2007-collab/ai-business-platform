import { api } from "./api/client";
import type { DashboardStats } from "../types/search-orders";

export const dashboardService = {
  async getStats(): Promise<DashboardStats> {
    const { data: result } = await api.get<DashboardStats>("/dashboard/stats");
    return result;
  },
};
