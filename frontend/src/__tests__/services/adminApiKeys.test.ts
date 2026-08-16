import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  listAdminApiKeys,
  revokeAdminApiKey,
} from "@/app/services/adminApiKeys";

vi.mock("@/app/services/api/client", () => ({
  api: { get: vi.fn(), delete: vi.fn() },
}));

import { api } from "@/app/services/api/client";

describe("adminApiKeys service", () => {
  beforeEach(() => vi.clearAllMocks());

  it("listAdminApiKeys GET /admin/api-keys con user_id y active_only", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { items: [], total: 0 },
    });
    await listAdminApiKeys("user-uuid-1", true);
    expect(api.get).toHaveBeenCalledWith("/admin/api-keys", {
      params: { user_id: "user-uuid-1", active_only: true },
    });
  });

  it("listAdminApiKeys active_only=false", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { items: [], total: 0 },
    });
    await listAdminApiKeys("u2", false);
    expect(api.get).toHaveBeenCalledWith("/admin/api-keys", {
      params: { user_id: "u2", active_only: false },
    });
  });

  it("revokeAdminApiKey DELETE", async () => {
    (api.delete as ReturnType<typeof vi.fn>).mockResolvedValue({});
    await revokeAdminApiKey("key-id-9");
    expect(api.delete).toHaveBeenCalledWith("/admin/api-keys/key-id-9");
  });
});
