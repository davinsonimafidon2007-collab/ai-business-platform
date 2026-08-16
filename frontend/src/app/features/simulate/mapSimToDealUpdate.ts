import type { SimulateProfitResponse } from "@/app/services/simulateProfit";
import type { DealSimulationUpdate } from "@/app/services/deals";

/** Mapea una respuesta de simulación al cuerpo de updateDealSimulation. */
export function mapSimToDealUpdate(
  sim: SimulateProfitResponse
): DealSimulationUpdate {
  return {
    purchase_price: sim.purchase_price,
    estimated_sale_price: sim.estimated_sale_price ?? undefined,
    total_cost: sim.total_cost,
    net_profit: sim.net_profit,
    roi_percentage: sim.roi_percentage,
    profile_name: sim.profile_name,
  };
}
