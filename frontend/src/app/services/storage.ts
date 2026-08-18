"use client";

import { Capacitor } from "@capacitor/core";
import CryptoJS from "crypto-js";

export const SECURE_PREFIX = "abp_secure_";
const SECRET_KEY = process.env.NEXT_PUBLIC_STORAGE_SECRET || "default-secret-abp";

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

export function encryptData(data: string): string {
  return CryptoJS.AES.encrypt(data, SECRET_KEY).toString();
}

export function decryptData(encrypted: string): string {
  try {
    const bytes = CryptoJS.AES.decrypt(encrypted, SECRET_KEY);
    const decrypted = bytes.toString(CryptoJS.enc.Utf8);
    if (!decrypted) {
      // Fallback for legacy base64 encoded data
      if (typeof atob !== "undefined") {
        return decodeURIComponent(escape(atob(encrypted)));
      }
      return Buffer.from(encrypted, "base64").toString("utf-8");
    }
    return decrypted;
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
      return raw === null ? null : decryptData(raw);
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
      window.localStorage.setItem(SECURE_PREFIX + key, encryptData(value));
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
