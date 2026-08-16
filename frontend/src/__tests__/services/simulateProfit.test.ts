import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the axios api client
vi.mock("@/app/services/api/client", () => ({
  api: {
    post: vi.fn(),
  },
}));

import { api } from "@/app/services/api/client";
import { simulateProfit } from "@/app/services/simulateProfit";

describe("simulateProfit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("posts to the correct path with the full body", async () => {
    const mockResponse = {
      data: {
        profile_name: "SPAIN",
        purchase_price: 18000,
        estimated_sale_price: 24000,
        total_cost: 23280,
        net_profit: 720,
        roi_percentage: 3.09,
        recommendation: "CONSIDER",
        risk_level: "MEDIUM",
        transport_cost: 1200,
        registration_cost: 450,
        taxes: 1800,
        inspection_cost: 90,
        commission_cost: 720,
        repair_estimate: 540,
        miscellaneous_cost: 480,
        cost_lines: [
          { key: "purchase_price", label_es: "Precio de compra", amount: 18000 },
          { key: "transport_cost", label_es: "Transporte", amount: 1200 },
        ],
        coherence_warnings: [],
        recommendation_label_es: "Considerar",
        risk_label_es: "Medio",
      },
    };
    vi.mocked(api.post).mockResolvedValue(mockResponse as any);

    const result = await simulateProfit("vehicle-1", {
      profile_name: "SPAIN",
      purchase_price: 18000,
      estimated_sale_price: 24000,
    });

    expect(api.post).toHaveBeenCalledWith(
      "/vehicles/vehicle-1/simulate-profit",
      {
        profile_name: "SPAIN",
        purchase_price: 18000,
        estimated_sale_price: 24000,
      }
    );
    expect(result).toEqual(mockResponse.data);
  });

  it("includes only provided fields when partial body is sent", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: {} } as any);

    await simulateProfit("vehicle-1", { profile_name: "ES" });

    expect(api.post).toHaveBeenCalledWith(
      "/vehicles/vehicle-1/simulate-profit",
      { profile_name: "ES" }
    );
  });
});
