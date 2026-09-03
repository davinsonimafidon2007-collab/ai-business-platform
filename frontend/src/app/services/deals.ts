import { api } from "@/app/services/api/client";

/** Debe espejar app/models/deal.py::DealStatus (máquina de estados v2). */
export type DealStatus =
  | "NEW"
  | "ANALYZING"
  | "NEGOTIATING"
  | "WON"
  | "BOUGHT"
  | "IN_TRANSIT"
  | "REGISTERED"
  | "SOLD"
  | "LOST"
  | "CANCELLED";

export type Deal = {
  id: string;
  user_id: string;
  status: DealStatus;
  opportunity_id?: string | null;
  vehicle_id?: string | null;
  notes?: string | null;
  offer_price?: number | null;
  contact_channel?: string | null;
  last_sim_purchase_price?: number | null;
  last_sim_sale_price?: number | null;
  last_sim_total_cost?: number | null;
  last_sim_net_profit?: number | null;
  last_sim_roi?: number | null;
  last_sim_profile?: string | null;
  last_sim_at?: string | null;
  // --- TASK 3: snapshot de negociación ---
  negotiation_initial_offer?: number | null;
  negotiation_max_price?: number | null;
  negotiation_walk_away_price?: number | null;
  negotiation_recommendation?: string | null;
  negotiation_snapshot_at?: string | null;
  // --- TASK 3: cumplimiento físico ---
  actual_purchase_price?: number | null;
  bought_at?: string | null;
  transport_carrier?: string | null;
  transport_cost?: number | null;
  transport_started_at?: string | null;
  transport_completed_at?: string | null;
  registration_plate?: string | null;
  registration_cost?: number | null;
  actual_taxes?: number | null;
  registered_at?: string | null;
  sale_price?: number | null;
  buyer_name?: string | null;
  buyer_contact?: string | null;
  sold_at?: string | null;
  /** Beneficio REAL (distinto de last_sim_net_profit, que es una estimación). */
  actual_profit?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type DealSimulationUpdate = {
  purchase_price?: number;
  estimated_sale_price?: number;
  total_cost?: number;
  net_profit?: number;
  roi_percentage?: number;
  profile_name?: string;
};

export type DealListResponse = {
  items: Deal[];
  total: number;
  limit: number;
  offset: number;
};

export type DealFilters = {
  status?: DealStatus;
  opportunity_id?: string;
  limit?: number;
  offset?: number;
};

export async function fetchDeals(
  params: DealFilters = {}
): Promise<DealListResponse> {
  const { data } = await api.get<DealListResponse>("/deals", {
    params: {
      status: params.status || undefined,
      opportunity_id: params.opportunity_id || undefined,
      limit: params.limit ?? 50,
      offset: params.offset ?? 0,
    },
  });
  return data;
}

export async function createDeal(body: {
  opportunity_id?: string;
  vehicle_id?: string;
  source?: string;
  external_id?: string;
  notes?: string;
  contact_channel?: string;
}): Promise<Deal> {
  const { data } = await api.post<Deal>("/deals", body);
  return data;
}

export async function updateDealStatus(
  dealId: string,
  body: {
    status: DealStatus;
    notes?: string;
    offer_price?: number;
    // --- TASK 3: solo se usan al transicionar a la etapa correspondiente ---
    actual_purchase_price?: number;
    transport_carrier?: string;
    transport_cost?: number;
    registration_plate?: string;
    registration_cost?: number;
    actual_taxes?: number;
    sale_price?: number;
    buyer_name?: string;
    buyer_contact?: string;
  }
): Promise<Deal> {
  const { data } = await api.patch<Deal>(`/deals/${dealId}/status`, body);
  return data;
}

export async function updateDealSimulation(
  dealId: string,
  body: DealSimulationUpdate
): Promise<Deal> {
  const { data } = await api.patch<Deal>(
    `/deals/${dealId}/simulation`,
    body
  );
  return data;
}

/** Reporting de cartera: deals cerrados (real vs. previsto) + pipeline activo. */
export type PortfolioSummary = {
  by_status: Record<string, number>;
  sold_count: number;
  sold_actual_profit_sum?: number | null;
  sold_projected_profit_sum?: number | null;
  profit_variance_sum?: number | null;
  total_revenue?: number | null;
  total_invested?: number | null;
  pipeline_count: number;
  pipeline_projected_profit?: number | null;
};

export async function fetchPortfolioSummary(): Promise<PortfolioSummary> {
  const { data } = await api.get<PortfolioSummary>("/deals/reports/portfolio");
  return data;
}

/** Comparación previsto (última simulación) vs. real de un deal. */
export type DealVariance = {
  deal_id: string;
  status: DealStatus;
  projected_purchase_price?: number | null;
  actual_purchase_price?: number | null;
  projected_sale_price?: number | null;
  actual_sale_price?: number | null;
  projected_total_cost?: number | null;
  actual_total_cost?: number | null;
  projected_net_profit?: number | null;
  actual_net_profit?: number | null;
  profit_variance?: number | null;
  projected_roi_percentage?: number | null;
};

export async function fetchDealVariance(dealId: string): Promise<DealVariance> {
  const { data } = await api.get<DealVariance>(`/deals/${dealId}/variance`);
  return data;
}
