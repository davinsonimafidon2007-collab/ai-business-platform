import { api } from "@/app/services/api/client";

export type ProviderCanaryStatus = {
  success: boolean | null;
  message: string | null;
  finished_at: string | null;
  autoscout24: Record<string, unknown> | null;
  mobile_de: Record<string, unknown> | null;
  strict_mobile: boolean | null;
  mobile_status: string | null;
};

export type AdminSystemStatus = {
  redis_ok: boolean | null;
  canary: ProviderCanaryStatus;
};

export async function fetchAdminStatus(): Promise<AdminSystemStatus> {
  const { data } = await api.get<AdminSystemStatus>("/admin/status");
  return data;
}

export async function runProviderCanary(): Promise<AdminSystemStatus> {
  // Canary puede tardar (red real); timeout largo solo en esta llamada
  const { data } = await api.post<AdminSystemStatus>(
    "/admin/status/canary",
    null,
    { timeout: 120_000 }
  );
  return data;
}