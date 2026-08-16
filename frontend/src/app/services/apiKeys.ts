import { api } from "./api/client";

export type ApiKey = {
  id: string;
  name: string;
  prefix: string;
  scopes: string | null;
  description: string | null;
  expires_at: string | null;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
};

export type ApiKeyCreated = ApiKey & {
  api_key: string; // solo en respuesta de create
};

export type ApiKeyListResponse = {
  items: ApiKey[];
  total: number;
};

export type ApiKeyCreatePayload = {
  name: string;
  description?: string | null;
  scopes?: string | null;
  expires_at?: string | null;
};

export async function listApiKeys(): Promise<ApiKeyListResponse> {
  const { data } = await api.get<ApiKeyListResponse>("/auth/api-keys");
  return data;
}

export async function createApiKey(
  payload: ApiKeyCreatePayload
): Promise<ApiKeyCreated> {
  const { data } = await api.post<ApiKeyCreated>("/auth/api-keys", payload);
  return data;
}

export async function revokeApiKey(id: string): Promise<void> {
  await api.delete(`/auth/api-keys/${id}`);
}