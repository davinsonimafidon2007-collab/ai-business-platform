import { api } from "@/app/services/api/client";
import type { AxiosError } from "axios";

export type HealthChecks = {
  api?: string;
  database?: string;
  redis?: string;
  [key: string]: string | undefined;
};

export type HealthResponse = {
  status: string;
  version: string;
  providers: string[];
  checks: HealthChecks;
};

export async function fetchHealth(): Promise<HealthResponse> {
  try {
    const { data } = await api.get<HealthResponse>("/health");
    return data;
  } catch (err) {
    const ax = err as AxiosError<HealthResponse>;
    if (ax.response?.status === 503 && ax.response.data) {
      return ax.response.data;
    }
    throw err;
  }
}

