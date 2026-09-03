import { api } from "@/app/services/api/client";

export type DealStatus =
  | "NEW"
  | "CONTACTED"
  | "OFFER"
  | "WON"
  | "BOUGHT"
  | "IN_TRANSIT"
  | "REGISTERED"
  | "SOLD"
  | "LOST"
  | "DROPPED";

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
