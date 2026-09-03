import { useQuery } from "@tanstack/react-query";
import { fetchOpportunities, OpportunityFilters } from "@/app/services/opportunities";

export function useOpportunities(filters?: OpportunityFilters & { status?: string; recommendation?: string }) {
  // Compat: si llega status legacy (active/pending) no lo enviamos, solo recommendation
  const clean: any = { ...filters };
  if (clean.status && !clean.recommendation) {
    // Mapeo legacy status->recommendation no fiable, se ignora
    delete clean.status;
  }
  return useQuery({
    queryKey: ["opportunities", clean],
    queryFn: () => fetchOpportunities(clean),
    staleTime: 60_000,
  });
}
