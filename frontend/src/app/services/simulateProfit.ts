import { api } from "@/app/services/api/client";

export type CostLine = {
  key: string;
  label_es: string;
  amount: number;
};

export type SimulateProfitRequest = {
  profile_name?: string; // "SPAIN" | "ES" | "PORTUGAL" | "PT" | ...
  purchase_price?: number;
  estimated_sale_price?: number;
  /** "dealer"/"private"/...; si se omite usa vehicle.seller_type (TASK 2). */
  seller_type?: string;
  min_margin_percentage?: number;
  min_roi_percentage?: number;
  risk_buffer_percentage?: number;
};

export type SimulateProfitResponse = {
  profile_name: string;
  purchase_price: number;
  estimated_sale_price: number | null;
  total_cost: number;
  net_profit: number;
  roi_percentage: number;
  recommendation: string;
  risk_level: string;
  transport_cost: number;
  registration_cost: number;
  taxes: number;
  inspection_cost: number;
  commission_cost: number;
  repair_estimate: number;
  miscellaneous_cost: number;
  cost_lines?: CostLine[];
  coherence_warnings?: string[];
  recommendation_label_es?: string;
  risk_label_es?: string;
  /** Precio de compra máximo (EUR) que sigue cumpliendo el margen/ROI mínimos (TASK 2). */
  max_purchase_price?: number | null;
  max_purchase_price_binding_constraint?: string | null;
};

export async function simulateProfit(
  vehicleId: string,
  body: SimulateProfitRequest
): Promise<SimulateProfitResponse> {
  const { data } = await api.post<SimulateProfitResponse>(
    `/vehicles/${vehicleId}/simulate-profit`,
    body
  );
  return data;
}
