import { api } from "@/app/services/api/client";

export type OpportunityVehicle = {
  id: string;
  brand?: string | null;
  model?: string | null;
  year?: number | null;
  mileage?: number | null;
  price?: number | null;
  source?: string | null;
  external_id?: string | null;
  url?: string | null;
};

export type Opportunity = {
  id: string;
  vehicle?: OpportunityVehicle | null;
  score?: number | null;
  estimated_profit?: number | null;
  roi_percentage?: number | null;
  recommendation?: string | null;
  risk_level?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type OpportunityListResponse = {
  items: Opportunity[];
  total: number;
  limit: number;
  offset: number;
};

export type OpportunityFilters = {
  recommendation?: string;
  min_score?: number;
  min_roi?: number;
  limit?: number;
  offset?: number;
};

export async function fetchOpportunities(
  params: OpportunityFilters = {}
): Promise<OpportunityListResponse> {
  const { data } = await api.get<OpportunityListResponse>("/opportunities", {
    params: {
      recommendation: params.recommendation || undefined,
      min_score: params.min_score ?? undefined,
      min_roi: params.min_roi ?? undefined,
      limit: params.limit ?? 50,
      offset: params.offset ?? 0,
    },
  });
  return data;
}