import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  compareVersions,
  resolveUpdateStatus,
  getInstalledVersion,
} from "@/app/services/app-update";

// ---------------------------------------------------------------------------
// MOB-P3-002 — App Update Check
// ===========================================================================

describe("compareVersions", () => {
  it("returns -1 when a < b", () => {
    expect(compareVersions("1.0.0", "1.1.0")).toBe(-1);
    expect(compareVersions("1.0.0", "2.0.0")).toBe(-1);
  });

  it("returns 0 when equal", () => {
    expect(compareVersions("1.0.0", "1.0.0")).toBe(0);
    // versiones con distinto número de componentes también se comparan
    expect(compareVersions("1.0", "1.0.0")).toBe(0);
  });

  it("returns 1 when a > b", () => {
    expect(compareVersions("1.2.0", "1.1.0")).toBe(1);
    expect(compareVersions("2.0.0", "1.9.9")).toBe(1);
  });

  it("handles non-numeric segments as 0", () => {
    expect(compareVersions("1.0.x", "1.0.0")).toBe(0);
  });
});

describe("resolveUpdateStatus", () => {
  it("returns 'required' when installed < min", () => {
    expect(resolveUpdateStatus("1.0.0", "1.5.0", "1.6.0")).toBe("required");
  });

  it("returns 'recommended' when installed >= min but < latest", () => {
    expect(resolveUpdateStatus("1.5.0", "1.5.0", "1.6.0")).toBe("recommended");
  });

  it("returns 'up-to-date' when installed >= latest", () => {
    expect(resolveUpdateStatus("1.6.0", "1.5.0", "1.6.0")).toBe("up-to-date");
    expect(resolveUpdateStatus("1.7.0", "1.5.0", "1.6.0")).toBe("up-to-date");
  });
});

describe("getInstalledVersion", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_APP_VERSION", "");
  });

  it("uses NEXT_PUBLIC_APP_VERSION when set", () => {
    vi.stubEnv("NEXT_PUBLIC_APP_VERSION", "2.3.4");
    expect(getInstalledVersion()).toBe("2.3.4");
  });

  it("falls back to 1.0.0 when not set", () => {
    expect(getInstalledVersion()).toBe("1.0.0");
  });
});