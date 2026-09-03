import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the axios api client
vi.mock("@/app/services/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

import { api } from "@/app/services/api/client";
import {
  fetchDeals,
  createDeal,
  updateDealStatus,
  updateDealSimulation,
  fetchPortfolioSummary,
  fetchDealVariance,
} from "@/app/services/deals";

describe("deals service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("fetchDeals", () => {
    it("fetches deals with no filters", async () => {
      const mockResponse = {
        data: { items: [], total: 0, limit: 50, offset: 0 },
      };
      vi.mocked(api.get).mockResolvedValue(mockResponse as any);

      const result = await fetchDeals();

      expect(api.get).toHaveBeenCalledWith("/deals", {
        params: {
          status: undefined,
          limit: 50,
          offset: 0,
        },
      });
      expect(result).toEqual(mockResponse.data);
    });

    it("passes status filter", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: { items: [], total: 0, limit: 50, offset: 0 },
      } as any);

      await fetchDeals({ status: "NEGOTIATING" });

      expect(api.get).toHaveBeenCalledWith("/deals", {
        params: {
          status: "NEGOTIATING",
          limit: 50,
          offset: 0,
        },
      });
    });

    it("uses provided limit and offset", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: { items: [], total: 0, limit: 20, offset: 40 },
      } as any);

      await fetchDeals({ limit: 20, offset: 40 });

      expect(api.get).toHaveBeenCalledWith("/deals", {
        params: {
          status: undefined,
          limit: 20,
          offset: 40,
        },
      });
    });
  });

  describe("createDeal", () => {
    it("posts opportunity_id and vehicle_id", async () => {
      const mockDeal = {
        id: "deal-1",
        user_id: "user-1",
        status: "NEW",
        opportunity_id: "opp-1",
        vehicle_id: "veh-1",
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockDeal } as any);

      const result = await createDeal({
        opportunity_id: "opp-1",
        vehicle_id: "veh-1",
      });

      expect(api.post).toHaveBeenCalledWith("/deals", {
        opportunity_id: "opp-1",
        vehicle_id: "veh-1",
      });
      expect(result).toEqual(mockDeal);
    });

    it("posts with notes and contact_channel", async () => {
      vi.mocked(api.post).mockResolvedValue({
        data: { id: "deal-1", status: "NEW" },
      } as any);

      await createDeal({
        opportunity_id: "opp-1",
        notes: "cliente interesado",
        contact_channel: "email",
      });

      expect(api.post).toHaveBeenCalledWith("/deals", {
        opportunity_id: "opp-1",
        notes: "cliente interesado",
        contact_channel: "email",
      });
    });
  });

  describe("updateDealStatus", () => {
    it("patches status with deal id in path", async () => {
      const mockDeal = {
        id: "deal-1",
        user_id: "user-1",
        status: "ANALYZING",
      };
      vi.mocked(api.patch).mockResolvedValue({ data: mockDeal } as any);

      const result = await updateDealStatus("deal-1", { status: "ANALYZING" });

      expect(api.patch).toHaveBeenCalledWith("/deals/deal-1/status", {
        status: "ANALYZING",
      });
      expect(result).toEqual(mockDeal);
    });

    it("patches with notes and offer_price", async () => {
      vi.mocked(api.patch).mockResolvedValue({
        data: { id: "deal-1", status: "NEGOTIATING" },
      } as any);

      await updateDealStatus("deal-1", {
        status: "NEGOTIATING",
        notes: "oferta enviada",
        offer_price: 15000,
      });

      expect(api.patch).toHaveBeenCalledWith("/deals/deal-1/status", {
        status: "NEGOTIATING",
        notes: "oferta enviada",
        offer_price: 15000,
      });
    });
  });

  describe("updateDealSimulation", () => {
    it("patches simulation with deal id in path", async () => {
      const mockDeal = {
        id: "deal-1",
        user_id: "user-1",
        status: "NEW",
        last_sim_net_profit: 2500,
        last_sim_roi: 11.63,
        last_sim_profile: "SPAIN",
      };
      vi.mocked(api.patch).mockResolvedValue({ data: mockDeal } as any);

      const result = await updateDealSimulation("deal-1", {
        purchase_price: 18000,
        estimated_sale_price: 24000,
        total_cost: 21500,
        net_profit: 2500,
        roi_percentage: 11.63,
        profile_name: "SPAIN",
      });

      expect(api.patch).toHaveBeenCalledWith("/deals/deal-1/simulation", {
        purchase_price: 18000,
        estimated_sale_price: 24000,
        total_cost: 21500,
        net_profit: 2500,
        roi_percentage: 11.63,
        profile_name: "SPAIN",
      });
      expect(result).toEqual(mockDeal);
    });

    it("patches partial simulation body", async () => {
      vi.mocked(api.patch).mockResolvedValue({
        data: { id: "deal-1", status: "NEW" },
      } as any);

      await updateDealSimulation("deal-1", {
        net_profit: 1000,
        roi_percentage: 5,
      });

      expect(api.patch).toHaveBeenCalledWith("/deals/deal-1/simulation", {
        net_profit: 1000,
        roi_percentage: 5,
      });
    });
  });

  describe("fetchPortfolioSummary", () => {
    it("fetches the portfolio reporting endpoint", async () => {
      const mockSummary = {
        by_status: { SOLD: 1 },
        sold_count: 1,
        sold_actual_profit_sum: 2550,
        sold_projected_profit_sum: 2500,
        profit_variance_sum: 50,
        total_revenue: 19000,
        total_invested: 16450,
        pipeline_count: 0,
        pipeline_projected_profit: null,
      };
      vi.mocked(api.get).mockResolvedValue({ data: mockSummary } as any);

      const result = await fetchPortfolioSummary();

      expect(api.get).toHaveBeenCalledWith("/deals/reports/portfolio");
      expect(result).toEqual(mockSummary);
    });
  });

  describe("fetchDealVariance", () => {
    it("fetches variance for a single deal", async () => {
      const mockVariance = {
        deal_id: "deal-1",
        status: "BOUGHT",
        projected_purchase_price: 15000,
        actual_purchase_price: 14800,
        profit_variance: null,
      };
      vi.mocked(api.get).mockResolvedValue({ data: mockVariance } as any);

      const result = await fetchDealVariance("deal-1");

      expect(api.get).toHaveBeenCalledWith("/deals/deal-1/variance");
      expect(result).toEqual(mockVariance);
    });
  });
});
