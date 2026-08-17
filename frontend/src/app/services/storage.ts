"use client";

import { Capacitor } from "@capacitor/core";

export const SECURE_PREFIX = "abp_secure_";

let nativePreferences:
  | typeof import("@capacitor/preferences").Preferences
  | null = null;

async function getPreferences() {
  if (!nativePreferences) {
    const { Preferences } = await import("@capacitor/preferences");
    nativePreferences = Preferences;
  }
  return nativePreferences;
}

function isNativePlatform(): boolean {
  return Capacitor.isNativePlatform();
}

function encode(value: string): string {
  if (typeof btoa !== "undefined") {
    return btoa(unescape(encodeURIComponent(value)));
  }
  return Buffer.from(value, "utf-8").toString("base64");
}

function decode(value: string): string {
  try {
    if (typeof atob !== "undefined") {
      return decodeURIComponent(escape(atob(value)));
    }
    return Buffer.from(value, "base64").toString("utf-8");
  } catch {
    return "";
  }
}

export const secureStorage = {
  async get(key: string): Promise<string | null> {
    if (isNativePlatform()) {
      try {
        const Preferences = await getPreferences();
        const { value } = await Preferences.get({ key });
        return value ?? null;
      } catch (err) {
        console.warn("Native storage get failed, falling back to localStorage:", err);
      }
    }
    if (typeof window !== "undefined") {
      const raw = window.localStorage.getItem(SECURE_PREFIX + key);
      return raw === null ? null : decode(raw);
    }
    return null;
  },

  async set(key: string, value: string): Promise<void> {
    if (isNativePlatform()) {
      try {
        const Preferences = await getPreferences();
        await Preferences.set({ key, value });
        return;
      } catch (err) {
        console.warn("Native storage set failed, falling back to localStorage:", err);
      }
    }
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SECURE_PREFIX + key, encode(value));
    }
  },

  async remove(key: string): Promise<void> {
    if (isNativePlatform()) {
      try {
        const Preferences = await getPreferences();
        await Preferences.remove({ key });
        return;
      } catch (err) {
        console.warn("Native storage remove failed:", err);
      }
    }
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(SECURE_PREFIX + key);
    }
  },

  async clear(): Promise<void> {
    if (isNativePlatform()) {
      try {
        const Preferences = await getPreferences();
        await Preferences.clear();
      } catch (err) {
        console.warn("Native storage clear failed:", err);
      }
    } else if (typeof window !== "undefined") {
      Object.keys(window.localStorage)
        .filter((k) => k.startsWith(SECURE_PREFIX))
        .forEach((k) => window.localStorage.removeItem(k));
    }
  },
};
