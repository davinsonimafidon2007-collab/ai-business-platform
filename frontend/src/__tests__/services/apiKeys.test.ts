import { describe, it, expect, vi, beforeEach } from "vitest";
import { listApiKeys, createApiKey, revokeApiKey } from "@/app/services/apiKeys";

vi.mock("@/app/services/api/client", () => ({
  api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

import { api } from "@/app/services/api/client";

describe("apiKeys service", () => {
  beforeEach(() => vi.clearAllMocks());

  it("listApiKeys GET /auth/api-keys", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { items: [], total: 0 },
    });
    await listApiKeys();
    expect(api.get).toHaveBeenCalledWith("/auth/api-keys");
  });

  it("createApiKey POST body", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        id: "1",
        name: "test",
        prefix: "abp_live",
        scopes: null,
        description: null,
        expires_at: null,
        is_active: true,
        last_used_at: null,
        created_at: "2026-01-01T00:00:00Z",
        api_key: "abp_live_secret",
      },
    });
    const data = await createApiKey({ name: "test" });
    expect(api.post).toHaveBeenCalledWith("/auth/api-keys", { name: "test" });
    expect(data.api_key).toBe("abp_live_secret");
  });

  it("revokeApiKey DELETE", async () => {
    (api.delete as ReturnType<typeof vi.fn>).mockResolvedValue({});
    await revokeApiKey("abc");
    expect(api.delete).toHaveBeenCalledWith("/auth/api-keys/abc");
  });
});