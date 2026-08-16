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

export type JobMetricsRead = {
  name: string;
  interval: number;
  status: string;
  last_execution: string | null;
  next_execution: string | null;
  last_duration: number;
  execution_count: number;
  success_count: number;
  failure_count: number;
  consecutive_failures: number;
};

export type ProvidersStatus = {
  providers: string[];
  default_import_cost_profile: string;
  enable_es_market_fixture: boolean;
  enable_coches_net_fixture: boolean;
  enable_autoscout24_es: boolean;
};

export type AdminSystemStatus = {
  redis_ok: boolean | null;
  canary: ProviderCanaryStatus;
  jobs: JobMetricsRead[];
  providers: ProvidersStatus;
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