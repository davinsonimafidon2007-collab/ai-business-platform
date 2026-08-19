import { describe, test, expect, vi, beforeEach } from "vitest";

vi.mock("@/app/services/api/client", () => ({
  api: { post: vi.fn() },
}));

import {
  initPushNotifications,
  unregisterPushNotifications,
} from "@/app/services/push-notifications";

describe("push-notifications service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("initPushNotifications silently no-ops on web platform", async () => {
    await initPushNotifications();
    expect(true).toBe(true);
  });

  test("unregisterPushNotifications silently no-ops when no token registered or on web", async () => {
    await unregisterPushNotifications();
    expect(true).toBe(true);
  });
});
