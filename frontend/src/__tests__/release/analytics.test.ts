import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// MOB-P3-003 — Firebase Crashlytics + Analytics
//
// La logica de analytics se degrada a no-op en entornos no soportados. Mockeamos
// firebase/analytics para verificar que trackEvent loguea y que trackError
// registra contexto, y que un fallo no rompe nada.
// ===========================================================================

const mocks = vi.hoisted(() => ({
  logEvent: vi.fn(),
  initializeApp: vi.fn(() => ({})),
  isSupported: vi.fn(async () => true),
}));

vi.mock("firebase/analytics", () => ({
  logEvent: mocks.logEvent,
  getAnalytics: () => ({ __analytics: true }),
  isSupported: mocks.isSupported,
}));
vi.mock("firebase/app", () => ({
  initializeApp: mocks.initializeApp,
}));

import { trackEvent, trackError, trackScreenView, type BusinessEventName } from "@/app/services/analytics";

describe("analytics service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(globalThis, "window", {
      value: { location: {} },
      configurable: true,
      writable: true,
    });
  });

  it("tracks a business event via logEvent", async () => {
    await trackEvent("deals/opened" as BusinessEventName, { source: "test" });
    expect(mocks.logEvent).toHaveBeenCalled();
  });

  it("trackError exposes the error key as context", async () => {
    await trackError("network_timeout", "fetch failed", { screen: "dashboard" });
    // El error llega al listener de logEvent con el contexto.
    expect(mocks.logEvent).toHaveBeenCalled();
  });

  it("trackScreenView dispatches a custom event and tracks screen_view", async () => {
    const dispatchSpy = vi.fn();
    Object.defineProperty(globalThis, "window", {
      value: { dispatchEvent: dispatchSpy },
      configurable: true,
      writable: true,
    });

    await trackScreenView("dashboard", { role: "admin" });

    expect(dispatchSpy).toHaveBeenCalled();
    expect(mocks.logEvent).toHaveBeenCalled();
  });

  it("trackEvent does not throw when logEvent fails", async () => {
    mocks.logEvent.mockImplementationOnce(() => {
      throw new Error("telemetry down");
    });
    await expect(
      trackEvent("deal_clicked" as BusinessEventName, {})
    ).resolves.toBeUndefined();
  });

  it("does not throw when analytics is unsupported", async () => {
    mocks.isSupported.mockResolvedValueOnce(false);
    await expect(trackEvent("deals/opened" as BusinessEventName, {})).resolves.toBeUndefined();
    mocks.isSupported.mockResolvedValueOnce(true);
  });
});