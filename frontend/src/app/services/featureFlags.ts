import { api } from "@/app/services/api/client";

export type FeatureFlag = {
  id: string;
  key: string;
  value: boolean;
  description: string | null;
  updated_at: string;
};

export async function fetchFeatureFlags(): Promise<FeatureFlag[]> {
  const { data } = await api.get<FeatureFlag[]>("/admin/feature-flags");
  return data;
}

export async function createFeatureFlag(input: {
  key: string;
  value?: boolean;
  description?: string | null;
}): Promise<FeatureFlag> {
  const { data } = await api.post<FeatureFlag>("/admin/feature-flags", input);
  return data;
}

export async function updateFeatureFlag(input: {
  key: string;
  value: boolean;
  description?: string | null;
}): Promise<FeatureFlag> {
  const { data } = await api.patch<FeatureFlag>(
    `/admin/feature-flags/${encodeURIComponent(input.key)}`,
    { value: input.value, description: input.description }
  );
  return data;
}

export async function deleteFeatureFlag(key: string): Promise<void> {
  await api.delete(`/admin/feature-flags/${key}`);
}