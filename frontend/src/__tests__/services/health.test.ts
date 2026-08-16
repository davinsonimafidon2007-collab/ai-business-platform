import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/app/services/api/client", () => ({
  api: { get: vi.fn() },
}));

import { api } from "@/app/services/api/client";
import { fetchHealth } from "@/app/services/health";

describe("fetchHealth", () => {
  beforeEach(() => vi.clearAllMocks());

  it("maps composite health body", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        status: "degraded",
        version: "0.0.0-test",
        providers: ["mobile_de"],
        checks: { api: "ok", database: "ok", redis: "disabled" },
      },
    });

    const h = await fetchHealth();

    expect(h.status).toBe("degraded");
    expect(h.checks.redis).toBe("disabled");
  });

  it("tolerates 503 and returns body", async () => {
    const axErr = new Error("Service Unavailable") as any;
    axErr.response = {
      status: 503,
      data: {
        status: "error",
        version: "0.0.0-test",
        providers: [],
        checks: { api: "ok", database: "error", redis: "disabled" },
      },
    };
    vi.mocked(api.get).mockRejectedValue(axErr);

    const h = await fetchHealth();

    expect(h.status).toBe("error");
    expect(h.checks.database).toBe("error");
  });

  it("re-throws non-503 errors", async () => {
    const axErr = new Error("Forbidden") as any;
    axErr.response = {
      status: 403,
      data: null,
    };
    vi.mocked(api.get).mockRejectedValue(axErr);

    await expect(fetchHealth()).rejects.toMatchObject({
      response: { status: 403 },
    });
  });
});

