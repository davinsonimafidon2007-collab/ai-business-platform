import { useQuery } from "@tanstack/react-query";
import { fetchOpportunities, OpportunityFilters } from "@/app/services/opportunities";

export function useOpportunities(filters?: OpportunityFilters & { status?: string }) {
  return useQuery({
    queryKey: ["opportunities", filters],
    queryFn: () => fetchOpportunities(filters),
    staleTime: 60_000,
  });
}
