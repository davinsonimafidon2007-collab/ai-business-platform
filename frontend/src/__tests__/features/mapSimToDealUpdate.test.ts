import { describe, it, expect } from "vitest";
import { mapSimToDealUpdate } from "@/app/features/simulate/mapSimToDealUpdate";
import type { SimulateProfitResponse } from "@/app/services/simulateProfit";

const baseSim: SimulateProfitResponse = {
  profile_name: "SPAIN",
  purchase_price: 18000,
  estimated_sale_price: 24000,
  total_cost: 21500,
  net_profit: 2500,
  roi_percentage: 11.63,
  recommendation: "BUY_NOW",
  risk_level: "LOW",
  transport_cost: 500,
  registration_cost: 800,
  taxes: 1200,
  inspection_cost: 150,
  commission_cost: 300,
  repair_estimate: 0,
  miscellaneous_cost: 0,
};

describe("mapSimToDealUpdate", () => {
  it("mapea todos los campos al cuerpo de updateDealSimulation", () => {
    expect(mapSimToDealUpdate(baseSim)).toEqual({
      purchase_price: 18000,
      estimated_sale_price: 24000,
      total_cost: 21500,
      net_profit: 2500,
      roi_percentage: 11.63,
      profile_name: "SPAIN",
    });
  });

  it("convierte estimated_sale_price null a undefined", () => {
    const sim = { ...baseSim, estimated_sale_price: null };
    expect(mapSimToDealUpdate(sim)).toEqual({
      purchase_price: 18000,
      estimated_sale_price: undefined,
      total_cost: 21500,
      net_profit: 2500,
      roi_percentage: 11.63,
      profile_name: "SPAIN",
    });
  });
});
