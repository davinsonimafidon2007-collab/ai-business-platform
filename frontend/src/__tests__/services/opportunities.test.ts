import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the axios api client
vi.mock("@/app/services/api/client", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from "@/app/services/api/client";
import { fetchOpportunities } from "@/app/services/opportunities";

describe("fetchOpportunities", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches opportunities with no filters", async () => {
    const mockResponse = {
      data: {
        items: [],
        total: 0,
        limit: 50,
        offset: 0,
      },
    };
    vi.mocked(api.get).mockResolvedValue(mockResponse as any);

    const result = await fetchOpportunities();

    expect(api.get).toHaveBeenCalledWith("/opportunities", {
      params: {
        recommendation: undefined,
        min_score: undefined,
        min_roi: undefined,
        limit: 50,
        offset: 0,
      },
    });
    expect(result).toEqual(mockResponse.data);
  });

  it("passes recommendation filter", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0, limit: 50, offset: 0 } } as any);

    await fetchOpportunities({ recommendation: "BUY_NOW" });

    expect(api.get).toHaveBeenCalledWith("/opportunities", {
      params: {
        recommendation: "BUY_NOW",
        min_score: undefined,
        min_roi: undefined,
        limit: 50,
        offset: 0,
      },
    });
  });

  it("passes min_score filter", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0, limit: 50, offset: 0 } } as any);

    await fetchOpportunities({ min_score: 80 });

    expect(api.get).toHaveBeenCalledWith("/opportunities", {
      params: {
        recommendation: undefined,
        min_score: 80,
        min_roi: undefined,
        limit: 50,
        offset: 0,
      },
    });
  });

  it("passes min_roi filter", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0, limit: 50, offset: 0 } } as any);

    await fetchOpportunities({ min_roi: 15 });

    expect(api.get).toHaveBeenCalledWith("/opportunities", {
      params: {
        recommendation: undefined,
        min_score: undefined,
        min_roi: 15,
        limit: 50,
        offset: 0,
      },
    });
  });

  it("uses provided limit and offset", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0, limit: 20, offset: 40 } } as any);

    await fetchOpportunities({ limit: 20, offset: 40 });

    expect(api.get).toHaveBeenCalledWith("/opportunities", {
      params: {
        recommendation: undefined,
        min_score: undefined,
        min_roi: undefined,
        limit: 20,
        offset: 40,
      },
    });
  });
});