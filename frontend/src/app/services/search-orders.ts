import { api } from "./api/client";
import type {
  CreateSearchOrderRequest,
  SearchOrder,
  SearchOrderDetail,
} from "../types/search-orders";

export const searchOrdersService = {
  async create(data: CreateSearchOrderRequest): Promise<SearchOrder> {
    const { data: result } = await api.post<SearchOrder>("/search-orders", data);
    return result;
  },

  async list(): Promise<SearchOrder[]> {
    const { data: result } = await api.get<SearchOrder[]>("/search-orders");
    return result;
  },

  async get(orderId: string): Promise<SearchOrderDetail> {
    const { data: result } = await api.get<SearchOrderDetail>(`/search-orders/${orderId}`);
    return result;
  },

  async newCount(): Promise<number> {
    const { data: result } = await api.get<{ new_count: number }>("/search-orders/new-count");
    return result.new_count;
  },

  async markSeen(orderId: string): Promise<SearchOrder> {
    const { data: result } = await api.post<SearchOrder>(`/search-orders/${orderId}/seen`);
    return result;
  },

  async remove(orderId: string): Promise<void> {
    await api.delete(`/search-orders/${orderId}`);
  },
};
