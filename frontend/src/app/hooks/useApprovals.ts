import { useQuery } from "@tanstack/react-query";

interface Approval {
  id: string;
  opportunity_id: string;
  title: string;
  category: string;
  description: string;
  detail?: string;
  priority: "ALTO" | "MEDIO" | "BAJO";
  status: "pending" | "approved" | "rejected";
  created_at: string;
  image?: string;
}

async function fetchApprovals(): Promise<Approval[]> {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${API_BASE}/api/v1/approvals`);
  if (!res.ok) throw new Error("Failed to fetch approvals");
  return res.json();
}

export function useApprovals() {
  return useQuery({
    queryKey: ["approvals"],
    queryFn: fetchApprovals,
    staleTime: 30_000,
  });
}
