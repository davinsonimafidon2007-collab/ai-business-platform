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

      await fetchDeals({ status: "OFFER" });

      expect(api.get).toHaveBeenCalledWith("/deals", {
        params: {
          status: "OFFER",
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
        status: "CONTACTED",
      };
      vi.mocked(api.patch).mockResolvedValue({ data: mockDeal } as any);

      const result = await updateDealStatus("deal-1", { status: "CONTACTED" });

      expect(api.patch).toHaveBeenCalledWith("/deals/deal-1/status", {
        status: "CONTACTED",
      });
      expect(result).toEqual(mockDeal);
    });

    it("patches with notes and offer_price", async () => {
      vi.mocked(api.patch).mockResolvedValue({
        data: { id: "deal-1", status: "OFFER" },
      } as any);

      await updateDealStatus("deal-1", {
        status: "OFFER",
        notes: "oferta enviada",
        offer_price: 15000,
      });

expect(api.patch).toHaveBeenCalledWith("/deals/deal-1/status", {
        status: "OFFER",
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
});
