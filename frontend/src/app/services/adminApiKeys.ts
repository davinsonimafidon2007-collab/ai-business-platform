import { api } from "@/app/services/api/client";
import type { ApiKey, ApiKeyListResponse } from "@/app/services/apiKeys";

export type { ApiKey, ApiKeyListResponse };

export async function listAdminApiKeys(
  userId: string,
  activeOnly = true
): Promise<ApiKeyListResponse> {
  const { data } = await api.get<ApiKeyListResponse>("/admin/api-keys", {
    params: { user_id: userId, active_only: activeOnly },
  });
  return data;
}

export async function revokeAdminApiKey(id: string): Promise<void> {
  await api.delete(`/admin/api-keys/${id}`);
}
