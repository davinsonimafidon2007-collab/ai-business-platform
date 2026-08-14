<<<<<<< ours
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
||||||| base
=======
import { Capacitor } from "@capacitor/core";
import { Preferences } from "@capacitor/preferences";

/**
 * secureStorage — almacenamiento seguro de credenciales/sensibles.
 *
 * - En plataforma nativa (Capacitor) delega en `@capacitor/preferences`
 *   (persistencia segura del WebView).
 * - En web/fallback persiste en localStorage con ofuscación base64 (no
 *   texto plano) bajo el prefijo `abp_secure_` para no dejar los tokens
 *   legibles.
 *
 * Todas las operaciones son async y devuelven Promesas para que el contrato
 * sea idéntico tanto en nativo como en web.
 */

export const SECURE_PREFIX = "abp_secure_";

const isNative = (): boolean => Capacitor.isNativePlatform();

// UTF-8 → base64 seguro (btoa no soporta multibyte directamente).
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
  async set(key: string, value: string): Promise<void> {
    if (isNative()) {
      await Preferences.set({ key, value });
      return;
    }
    localStorage.setItem(SECURE_PREFIX + key, encode(value));
  },

  async get(key: string): Promise<string | null> {
    if (isNative()) {
      const { value } = await Preferences.get({ key });
      return value ?? null;
    }
    const raw = localStorage.getItem(SECURE_PREFIX + key);
    return raw === null ? null : decode(raw);
  },

  async remove(key: string): Promise<void> {
    if (isNative()) {
      await Preferences.remove({ key });
      return;
    }
    localStorage.removeItem(SECURE_PREFIX + key);
  },

  async clear(): Promise<void> {
    if (isNative()) {
      await Preferences.clear();
      return;
    }
    Object.keys(localStorage)
      .filter((k) => k.startsWith(SECURE_PREFIX))
      .forEach((k) => localStorage.removeItem(k));
  },
};
>>>>>>> theirs
