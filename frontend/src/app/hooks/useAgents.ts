import { useQuery } from "@tanstack/react-query";

interface Agent {
  id: string;
  name: string;
  role: string;
  description: string;
  status: "active" | "idle" | "busy" | "error";
  tasks_completed: number;
  avg_time: string;
  success_rate: number;
}

async function fetchAgents(): Promise<Agent[]> {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${API_BASE}/api/v1/agents`);
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}

export function useAgents() {
  return useQuery({
    queryKey: ["agents"],
    queryFn: fetchAgents,
    staleTime: 60_000,
  });
}
