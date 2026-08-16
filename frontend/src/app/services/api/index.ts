import { api } from "@/app/services/api/client";

export async function apiGet<T = any>(url: string, params?: Record<string, any>): Promise<T> {
  const { data } = await api.get<T>(url, { params });
  return data;
}

export async function apiPost<T = any>(url: string, body?: any): Promise<T> {
  const { data } = await api.post<T>(url, body);
  return data;
}

export async function apiPatch<T = any>(url: string, body?: any): Promise<T> {
  const { data } = await api.patch<T>(url, body);
  return data;
}

export async function apiDelete<T = any>(url: string): Promise<T> {
  const { data } = await api.delete<T>(url);
  return data;
}
