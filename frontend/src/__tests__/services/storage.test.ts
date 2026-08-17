import { describe, it, expect, vi, beforeEach } from "vitest";
import { secureStorage, SECURE_PREFIX } from "@/app/services/storage";

vi.mock("@capacitor/core", () => ({
  Capacitor: { isNativePlatform: vi.fn() },
}));
vi.mock("@capacitor/preferences", () => ({
  Preferences: { set: vi.fn(), get: vi.fn(), remove: vi.fn(), clear: vi.fn() },
}));

import { Capacitor } from "@capacitor/core";
import { Preferences } from "@capacitor/preferences";

function mockNative(value: boolean) {
  (Capacitor.isNativePlatform as any).mockReturnValue(value);
}

describe("secureStorage (web)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mockNative(false);
  });

  it("set/get roundtrips with base64 obfuscation (not plain text)", async () => {
    await secureStorage.set("token", "secret-value");
    const stored = window.localStorage.getItem(SECURE_PREFIX + "token");
    expect(stored).not.toBe("secret-value");
    expect(await secureStorage.get("token")).toBe("secret-value");
  });

  it("get returns null when the key is missing", async () => {
    expect(await secureStorage.get("missing")).toBeNull();
  });

  it("remove deletes the key", async () => {
    await secureStorage.set("token", "x");
    await secureStorage.remove("token");
    expect(window.localStorage.getItem(SECURE_PREFIX + "token")).toBeNull();
  });

  it("clear removes only secure-prefixed keys", async () => {
    window.localStorage.setItem("other", "keep");
    await secureStorage.set("a", "1");
    await secureStorage.set("b", "2");

    await secureStorage.clear();

    expect(window.localStorage.getItem("other")).toBe("keep");
    expect(window.localStorage.getItem(SECURE_PREFIX + "a")).toBeNull();
    expect(window.localStorage.getItem(SECURE_PREFIX + "b")).toBeNull();
  });

  it("decode returns an empty string on corrupt base64", async () => {
    window.localStorage.setItem(SECURE_PREFIX + "bad", "@@@notbase64@@@");
    expect(await secureStorage.get("bad")).toBe("");
  });
});

describe("secureStorage (native)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNative(true);
  });

  it("set delegates to Preferences", async () => {
    await secureStorage.set("token", "v");
    expect(Preferences.set).toHaveBeenCalledWith({ key: "token", value: "v" });
  });

  it("get delegates to Preferences and returns the value", async () => {
    (Preferences.get as any).mockResolvedValue({ value: "v" });
    expect(await secureStorage.get("token")).toBe("v");
  });

  it("get returns null when Preferences has no value", async () => {
    (Preferences.get as any).mockResolvedValue({ value: null });
    expect(await secureStorage.get("token")).toBeNull();
  });

  it("remove delegates to Preferences", async () => {
    await secureStorage.remove("token");
    expect(Preferences.remove).toHaveBeenCalledWith({ key: "token" });
  });

  it("clear delegates to Preferences", async () => {
    await secureStorage.clear();
    expect(Preferences.clear).toHaveBeenCalled();
  });
});
