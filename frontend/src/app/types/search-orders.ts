import type { SearchResultItem } from "./vehicle";

export type SearchOrderStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface SearchOrder {
  id: string;
  query: string;
  total_budget: number | null;
  max_purchase_price: number | null;
  status: SearchOrderStatus;
  results_count: number;
  new_count: number;
  error_message: string | null;
  created_at: string;
  last_run_at: string | null;
}

export interface SearchOrderVehicle {
  id: string;
  seen: boolean;
  result: SearchResultItem | null;
}

export interface SearchOrderDetail extends SearchOrder {
  vehicles: SearchOrderVehicle[];
}

export interface CreateSearchOrderRequest {
  query: string;
  total_budget?: number | null;
  profit_margin_min?: number;
  profile?: string;
  filters?: Record<string, unknown>;
}

export interface DashboardRecentOrder {
  id: string;
  query: string;
  status: SearchOrderStatus;
  results_count: number;
  new_count: number;
  max_purchase_price: number | null;
  error_message: string | null;
  created_at: string | null;
  last_run_at: string | null;
}

export interface DashboardRecentVehicle {
  id: string;
  brand: string;
  model: string;
  year: number | null;
  price: number | null;
  currency: string | null;
  image_url: string | null;
  score: number | null;
  classification: string | null;
  estimated_profit: number | null;
  estimated_total_cost: number | null;
  has_evaluation: boolean;
  created_at: string | null;
}

export interface DashboardStats {
  total_searches: number;
  recent_searches: number;
  total_vehicles: number;
  total_inspections: number;
  completed_inspections: number;
  total_opportunities: number;
  average_results_per_search: number;
  average_execution_time: number;
  new_search_results: number;
  recent_orders: DashboardRecentOrder[];
  recent_vehicles: DashboardRecentVehicle[];
}
