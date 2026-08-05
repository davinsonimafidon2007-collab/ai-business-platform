import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/app/services/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from "@/app/services/api/client";
import { fetchAdminStatus, runProviderCanary } from "@/app/services/adminStatus";

describe("adminStatus service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetchAdminStatus llama GET /admin/status", async () => {
    const payload = {
      redis_ok: true,
      canary: {
        success: true,
        message: "ok",
        finished_at: "2026-08-04T12:00:00Z",
        autoscout24: { count: 5 },
        mobile_de: null,
        strict_mobile: false,
        mobile_status: "skipped",
      },
    };
    vi.mocked(api.get).mockResolvedValue({ data: payload } as any);

    const data = await fetchAdminStatus();

    expect(api.get).toHaveBeenCalledWith("/admin/status");
    expect(data.redis_ok).toBe(true);
    expect(data.canary.success).toBe(true);
  });

  it("runProviderCanary llama POST /admin/status/canary", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { redis_ok: true, canary: { success: false, message: "fail" } },
    } as any);

    const data = await runProviderCanary();

    expect(api.post).toHaveBeenCalledWith(
      "/admin/status/canary",
      null,
      expect.objectContaining({ timeout: 120_000 })
    );
    expect(data.canary.success).toBe(false);
  });
});