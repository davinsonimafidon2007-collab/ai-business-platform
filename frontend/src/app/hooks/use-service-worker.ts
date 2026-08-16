"use client";

import { useEffect } from "react";

/**
 * Service Worker registration hook — TASK-016 (FASE 5).
 *
 * Registers the service worker for offline support. Should be called once at
 * app startup (Providers). No-op in environments without SW support.
 */

export function useServiceWorker() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
      return;
    }

    navigator.serviceWorker
      .register("/service-worker.js")
      .then((registration) => {
        console.log("[SW] Registered:", registration.scope);
      })
      .catch((error) => {
        console.error("[SW] Registration failed:", error);
      });
  }, []);
}
