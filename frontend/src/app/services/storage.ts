"use client";

/**
 * MOB-P0-003: Secure storage wrapper.
 *
 * - Web: usa localStorage (única opción disponible en navegador/WebView).
 * - Nativo (Capacitor): usa Capacitor Preferences, que persiste en el
 *   almacenamiento nativo de la plataforma (Android SharedPreferences /
 *   iOS NSUserDefaults) en vez de localStorage expuesto a JS.
 *
 * Las claves conservan el contrato previo (`access_token`, `refresh_token`,
 * `user`) para no invalidar sesiones ya guardadas.
 */

import { Capacitor } from "@capacitor/core";

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

const isNative = Capacitor.isNativePlatform();

export const secureStorage = {
  async get(key: string): Promise<string | null> {
    if (isNative) {
      try {
        const Preferences = await getPreferences();
        const { value } = await Preferences.get({ key });
        return value ?? null;
      } catch (err) {
        console.warn("Native storage get failed, falling back to localStorage:", err);
      }
    }
    if (typeof window !== "undefined") {
      return window.localStorage.getItem(key);
    }
    return null;
  },

  async set(key: string, value: string): Promise<void> {
    if (isNative) {
      try {
        const Preferences = await getPreferences();
        await Preferences.set({ key, value });
        return;
      } catch (err) {
        console.warn("Native storage set failed, falling back to localStorage:", err);
      }
    }
    if (typeof window !== "undefined") {
      window.localStorage.setItem(key, value);
    }
  },

  async remove(key: string): Promise<void> {
    if (isNative) {
      try {
        const Preferences = await getPreferences();
        await Preferences.remove({ key });
        return;
      } catch (err) {
        console.warn("Native storage remove failed:", err);
      }
    }
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(key);
    }
  },

  async clear(): Promise<void> {
    if (isNative) {
      try {
        const Preferences = await getPreferences();
        await Preferences.clear();
      } catch (err) {
        console.warn("Native storage clear failed:", err);
      }
    }
  },
};