import { api } from "@/app/services/api/client";

export async function fetchAdminMetrics(): Promise<string> {
  // El endpoint devuelve text/plain en formato Prometheus exposition.
  const { data } = await api.get<string>("/admin/metrics", {
    responseType: "text",
  });
  return typeof data === "string" ? data : String(data);
}