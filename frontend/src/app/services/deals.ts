import { api } from "@/app/services/api/client";

export type DealStatus =
  | "NEW"
  | "CONTACTED"
  | "OFFER"
  | "WON"
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
  created_at?: string | null;
  updated_at?: string | null;
};

export type DealListResponse = {
  items: Deal[];
  total: number;
  limit: number;
  offset: number;
};

export type DealFilters = {
  status?: DealStatus;
  limit?: number;
  offset?: number;
};

export async function fetchDeals(
  params: DealFilters = {}
): Promise<DealListResponse> {
  const { data } = await api.get<DealListResponse>("/deals", {
    params: {
      status: params.status || undefined,
      limit: params.limit ?? 50,
      offset: params.offset ?? 0,
    },
  });
  return data;
}

export async function createDeal(body: {
  opportunity_id?: string;
  vehicle_id?: string;
  notes?: string;
  contact_channel?: string;
}): Promise<Deal> {
  const { data } = await api.post<Deal>("/deals", body);
  return data;
}

export async function updateDealStatus(
  dealId: string,
  body: { status: DealStatus; notes?: string; offer_price?: number }
): Promise<Deal> {
  const { data } = await api.patch<Deal>(`/deals/${dealId}/status`, body);
  return data;
}
