import { api } from "@/app/services/api/client";

export type SimulateProfitRequest = {
  profile_name?: string; // "SPAIN" | "ES" | "PORTUGAL" | "PT" | ...
  purchase_price?: number;
  estimated_sale_price?: number;
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
