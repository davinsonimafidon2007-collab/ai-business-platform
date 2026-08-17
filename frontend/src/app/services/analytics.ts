"use client";

import { getAnalytics, logEvent, isSupported } from "firebase/analytics";
import { initializeApp, type FirebaseApp } from "firebase/app";

/**
 * analytics — wrapper tipado de Firebase Analytics + Crashlytics de negocio.
 *
 * Estrategia "no-crash": la inicialización es perezosa y solo en cliente, y
 * cualquier fallo (sin navegador, analytics no soportado, red bloqueada) se
 * degrada silenciosamente a no-op. El resto de la app nunca debe romperse por
 * un problema de telemetría.
 *
 * - ``trackEvent``       → evento de negocio tipado (vía Firebase Analytics).
 * - ``trackError``       → registro de errores con contexto (named-crash).
 * - ``trackScreenView``  → conveniencia para cambios de pantalla.
 */

const firebaseConfig = {
  apiKey:
    process.env.NEXT_PUBLIC_FIREBASE_API_KEY ||
    "AIzaSyDKQU1xQlH_v6Y79-69phr2jsQ4QWuWe_o",
  authDomain:
    process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN ||
    "ai-business-platform-e7043.firebaseapp.com",
  projectId:
    process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID ||
    "ai-business-platform-e7043",
  storageBucket:
    process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET ||
    "ai-business-platform-e7043.firebasestorage.app",
  messagingSenderId:
    process.env.NEXT_PUBLIC_FIREBASE_SENDER_ID || "983773208764",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || undefined,
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID || undefined,
};

/** Eventos de negocio tipados (extender según crezcan los casos de uso). */
export type BusinessEventName =
  | "search_performed"
  | "deal_clicked"
  | "vehicle_viewed"
  | "order_created"
  | "inspection_started"
  | "login_success"
  | "purchase_completed"
  | "screen_view"
  | "error_logged";

export interface AnalyticsEventParams {
  [key: string]: string | number | boolean | undefined;
}

let appCache: FirebaseApp | null = null;
let analyticsCache: ReturnType<typeof getAnalytics> | null = null;
let supportedCache: boolean | null = null;
let disabled = false;

function getApp(): FirebaseApp | null {
  if (appCache) return appCache;
  if (typeof window === "undefined") return null;
  try {
    appCache = initializeApp(firebaseConfig);
    return appCache;
  } catch {
    return null;
  }
}

async function getAnalyticsInstance() {
  if (disabled) return null;
  if (analyticsCache) return analyticsCache;
  if (typeof window === "undefined") return null;

  try {
    if (supportedCache === null) {
      supportedCache = await isSupported();
    }
    if (!supportedCache) {
      disabled = true;
      return null;
    }
    const app = getApp();
    if (!app) return null;
    analyticsCache = getAnalytics(app);
    return analyticsCache;
  } catch {
    disabled = true;
    return null;
  }
}

/** Registra un evento de negocio tipado. Si Analytics no está disponible, no-op. */
export async function trackEvent(
  name: BusinessEventName,
  params: AnalyticsEventParams = {}
): Promise<void> {
  const analytics = await getAnalyticsInstance();
  if (!analytics) return;
  try {
    // `name` es BusinessEventName (incluye 'screen_view' y eventos de negocio
    // custom). Firebase tipa 'screen_view' como evento predefinido en otro
    // overload, lo que rompe la unión → casteo a `never` (no altera runtime).
    logEvent(analytics, name as never, params);
  } catch {
    // nunca romper la app por telemetría
  }
}

/** Registra un error con contexto (actúa como Crashlytics-named-crash). */
export async function trackError(
  errorKey: string,
  message?: string,
  context: AnalyticsEventParams = {}
): Promise<void> {
  await trackEvent("error_logged", {
    ...context,
    error_key: errorKey,
    error_message: message ?? "",
  });
}

/** Conveniencia: evento de pantalla. */
export async function trackScreenView(
  screen: string,
  context: AnalyticsEventParams = {}
): Promise<void> {
  if (typeof window === "undefined") return;
  try {
    window.dispatchEvent(
      new CustomEvent("abp:screen_view", {
        detail: { screen, ...context },
      })
    );
  } catch {
    // no-op
  }
  await trackEvent("screen_view", { screen, ...context });
}