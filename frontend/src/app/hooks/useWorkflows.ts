import { useQuery } from "@tanstack/react-query";

interface Workflow {
  id: string;
  name: string;
  description: string;
  status: "running" | "paused" | "failed" | "completed";
  phases: number;
  completed_phases: number;
  last_run: string;
}

async function fetchWorkflows(): Promise<Workflow[]> {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${API_BASE}/api/v1/workflows`);
  if (!res.ok) throw new Error("Failed to fetch workflows");
  return res.json();
}

export function useWorkflows() {
  return useQuery({
    queryKey: ["workflows"],
    queryFn: fetchWorkflows,
    staleTime: 60_000,
  });
}
