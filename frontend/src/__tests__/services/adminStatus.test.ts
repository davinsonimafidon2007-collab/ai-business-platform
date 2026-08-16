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
      jobs: [],
      providers: {
        providers: ["mobile_de", "es_market_fixture"],
        default_import_cost_profile: "SPAIN",
        enable_es_market_fixture: true,
        enable_coches_net_fixture: true,
        enable_autoscout24_es: false,
      },
    };
    vi.mocked(api.get).mockResolvedValue({ data: payload } as any);

    const data = await fetchAdminStatus();

    expect(api.get).toHaveBeenCalledWith("/admin/status");
    expect(data.redis_ok).toBe(true);
    expect(data.canary.success).toBe(true);
    expect(data.jobs).toEqual([]);
    expect(data.providers.providers).toEqual([
      "mobile_de",
      "es_market_fixture",
    ]);
    expect(data.providers.default_import_cost_profile).toBe("SPAIN");
    expect(data.providers.enable_es_market_fixture).toBe(true);
    expect(data.providers.enable_coches_net_fixture).toBe(true);
    expect(data.providers.enable_autoscout24_es).toBe(false);

  });

  it("fetchAdminStatus devuelve jobs con consecutive_failures", async () => {
    const payload = {
      redis_ok: true,
      canary: { success: false, message: "ok", mobile_status: "ok" },
      jobs: [
        {
          name: "refresh_market_cache",
          interval: 3600,
          status: "failed",
          last_execution: "2026-08-04T12:00:00Z",
          next_execution: "2026-08-04T13:00:00Z",
          last_duration: 1.5,
          execution_count: 10,
          success_count: 7,
          failure_count: 3,
          consecutive_failures: 3,
        },
      ],
    };
    vi.mocked(api.get).mockResolvedValue({ data: payload } as any);

    const data = await fetchAdminStatus();

    expect(data.jobs).toHaveLength(1);
    expect(data.jobs[0].name).toBe("refresh_market_cache");
    expect(data.jobs[0].consecutive_failures).toBe(3);
  });

  it("runProviderCanary llama POST /admin/status/canary", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: {
        redis_ok: true,
        canary: { success: false, message: "fail" },
        jobs: [],
      },
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
