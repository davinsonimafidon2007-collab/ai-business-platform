import { describe, test, expect } from "vitest";
import {
  parseDeepLink,
  resolveDeepLinkRoute,
  deepLinkBuilder,
} from "@/app/hooks/use-deep-links";

describe("use-deep-links", () => {
  test("parseDeepLink parses valid scheme and web domain URLs", () => {
    const data = parseDeepLink("aibusiness://vehicle/v123?ref=alert");
    expect(data?.path).toBe("vehicle/v123");
    expect(data?.queryParams?.ref).toBe("alert");

    const webData = parseDeepLink("https://aibusiness.app/deal/d456");
    expect(webData?.path).toBe("deal/d456");

    const invalid = parseDeepLink("https://google.com/search");
    expect(invalid).toBeNull();
  });

  test("resolveDeepLinkRoute resolves known routes correctly", () => {
    expect(
      resolveDeepLinkRoute({ path: "vehicle/v123" })
    ).toBe("/vehicle/v123");
    expect(resolveDeepLinkRoute({ path: "deal/d456" })).toBe("/deal/d456");
    expect(resolveDeepLinkRoute({ path: "settings" })).toBe("/settings");
    expect(resolveDeepLinkRoute({ path: "dashboard" })).toBe("/dashboard");
    expect(resolveDeepLinkRoute({ path: "" })).toBe("/dashboard");
    expect(resolveDeepLinkRoute({ path: "unknown" })).toBeNull();
  });

  test("deepLinkBuilder constructs well-formed links", () => {
    expect(deepLinkBuilder.vehicle("123")).toBe("aibusiness://vehicle/123");
    expect(deepLinkBuilder.deal("456")).toBe("aibusiness://deal/456");
    expect(deepLinkBuilder.opportunity("789")).toBe("aibusiness://opportunity/789");
    expect(deepLinkBuilder.settings()).toBe("aibusiness://settings");
    expect(deepLinkBuilder.dashboard()).toBe("aibusiness://dashboard");
  });
});
