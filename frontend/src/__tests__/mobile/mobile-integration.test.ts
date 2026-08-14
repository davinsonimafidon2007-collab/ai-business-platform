import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// Mocks hoisteados — se usan en vi.mock (que Vitest mueve al tope del archivo).
// ---------------------------------------------------------------------------
const mocks = vi.hoisted(() => ({
  mockCapacitor: {
    isNativePlatform: vi.fn(() => false),
    getPlatform: vi.fn(() => "web"),
  },
  mockPreferences: {
    get: vi.fn(),
    set: vi.fn(),
    remove: vi.fn(),
    clear: vi.fn(),
  },
}));

vi.mock("@capacitor/core", () => ({ Capacitor: mocks.mockCapacitor }));
vi.mock("@capacitor/preferences", () => ({ Preferences: mocks.mockPreferences }));

// ---------------------------------------------------------------------------
// Importaciones reales (los mocks interceptan @capacitor/... internamente).
// ---------------------------------------------------------------------------
import { secureStorage, SECURE_PREFIX } from "@/app/services/storage";
import { offlineCache } from "@/app/hooks/use-offline";
import {
  parseDeepLink,
  resolveDeepLinkRoute,
  deepLinkBuilder,
} from "@/app/hooks/use-deep-links";
import { DataState } from "@/app/components/ui/data-states";

// ============================================================================
// MOB-P2-003 — Tests de Integración Móvil
// ============================================================================

describe("Secure Storage Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("should store and retrieve tokens", async () => {
    await secureStorage.set("access_token", "test-token-123");
    const result = await secureStorage.get("access_token");
    expect(result).toBe("test-token-123");
  });

  it("should obfuscate data in localStorage", async () => {
    await secureStorage.set("refresh_token", "secret");
    const raw = localStorage.getItem(SECURE_PREFIX + "refresh_token");
    expect(raw).not.toBe("secret");
    expect(raw).toBeTruthy();
  });

  it("should return null for missing keys", async () => {
    const result = await secureStorage.get("missing");
    expect(result).toBeNull();
  });
});

describe("Offline Cache Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("should cache and retrieve searches", async () => {
    await offlineCache.add({
      query: { key: "search", make: "Toyota" },
      results: [{ id: "1" }],
      resultCount: 1,
    });
    const cached = await offlineCache.findByQuery({
      key: "search",
      make: "Toyota",
    });
    expect(cached).not.toBeNull();
    expect(cached?.resultCount).toBe(1);
  });

  it("should deduplicate queries", async () => {
    const q = { key: "search", make: "Honda" };
    await offlineCache.add({
      query: q,
      results: [{ id: "1" }],
      resultCount: 1,
    });
    await offlineCache.add({
      query: q,
      results: [{ id: "2" }],
      resultCount: 1,
    });
    const all = await offlineCache.getAll();
    expect(
      all.filter((c) => JSON.stringify(c.query) === JSON.stringify(q)).length
    ).toBe(1);
  });

  it("should limit to 20 items", async () => {
    for (let i = 0; i < 25; i++) {
      await offlineCache.add({
        query: { key: "search", id: i },
        results: [{ id: String(i) }],
        resultCount: 1,
      });
    }
    expect((await offlineCache.getAll()).length).toBeLessThanOrEqual(20);
  });
});

describe("Deep Links Integration", () => {
  it("should parse aibusiness://vehicle/123", () => {
    const r = parseDeepLink("aibusiness://vehicle/123");
    expect(r?.path).toBe("vehicle/123");
  });

  it("should parse https URLs", () => {
    const r = parseDeepLink("https://aibusiness.app/vehicle/456");
    expect(r?.path).toBe("vehicle/456");
  });

  it("should reject invalid URLs", () => {
    expect(parseDeepLink("https://evil.com/hack")).toBeNull();
  });

  it("should resolve routes", () => {
    const data = parseDeepLink("aibusiness://vehicle/123");
    expect(resolveDeepLinkRoute(data!)).toBe("/vehicle/123");
  });

  it("should build deep links", () => {
    expect(deepLinkBuilder.vehicle("123")).toBe("aibusiness://vehicle/123");
    expect(deepLinkBuilder.deal("456")).toBe("aibusiness://deal/456");
  });
});

describe("Data States Integration", () => {
  it("should render loading", () => {
    render(
      React.createElement(DataState, {
        isLoading: true,
        isError: false,
        data: undefined,
        children: () => null,
      })
    );
    expect(screen.getByText("Cargando...")).toBeInTheDocument();
  });

  it("should render error with retry", () => {
    const onRetry = vi.fn();
    render(
      React.createElement(DataState, {
        isLoading: false,
        isError: true,
        data: undefined,
        error: new Error("fail"),
        onRetry,
        children: () => null,
      })
    );
    fireEvent.click(screen.getByText("Intentar de nuevo"));
    expect(onRetry).toHaveBeenCalled();
  });

  it("should render empty with action", () => {
    const onAction = vi.fn();
    render(
      React.createElement(DataState, {
        isLoading: false,
        isError: false,
        data: [],
        emptyProps: {
          icon: "inbox",
          title: "Empty",
          action: { label: "Create", onClick: onAction },
        },
        children: () => null,
      })
    );
    fireEvent.click(screen.getByText("Create"));
    expect(onAction).toHaveBeenCalled();
  });
});