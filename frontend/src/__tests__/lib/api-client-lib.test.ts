import api, { apiClient } from "@/lib/api-client";

describe("lib/api-client", () => {
  it("exports api and apiClient", () => {
    expect(apiClient).toBeDefined();
    expect(api).toBeDefined();
  });
});
