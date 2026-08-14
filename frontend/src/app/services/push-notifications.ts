"use client";

/**
 * MOB-P1-009 + MOB-P2-001: Push Notifications con Deep Links
 *
 * Registra el token FCM con el backend (MOB-P1-001) y navega desde
 * notificaciones a rutas internas vía deep links.
 */

import { Capacitor } from "@capacitor/core";
import { api } from "@/app/services/api/client";

let initialized = false;
let currentFcmToken: string | null = null;

/**
 * Initialize push notifications. Call once at app startup.
 * Silently no-ops on web or if plugin is not installed.
 */
export async function initPushNotifications(): Promise<void> {
  if (initialized) return;
  if (!Capacitor.isNativePlatform()) return;

  try {
    const { PushNotifications } = await import("@capacitor/push-notifications");

    const permission = await PushNotifications.requestPermissions();
    if (permission.receive !== "granted") {
      console.warn("[Push] Permission denied");
      return;
    }

    await PushNotifications.addListener("registration", async (token: { value: string }) => {
      currentFcmToken = token.value;
      console.log("[Push] Token:", token.value);
      try {
        await api.post("/notifications/register", {
          token: token.value,
          platform: Capacitor.getPlatform(),
        });
      } catch (err) {
        console.error("[Push] Failed to register token:", err);
      }
    });

    await PushNotifications.addListener("registrationError", (err: { error?: string }) => {
      console.error("[Push] Registration error:", err.error);
    });

    await PushNotifications.addListener("pushNotificationReceived", (notification: unknown) => {
      console.log("[Push] Received:", notification);
    });

    await PushNotifications.addListener(
      "pushNotificationActionPerformed",
      (action: { notification: { data?: { deepLink?: string } } }) => {
        console.log("[Push] Action performed:", action);
        const data = action.notification.data;
        if (data?.deepLink) {
          const event = new CustomEvent("deepLink:navigate", { detail: { url: data.deepLink } });
          window.dispatchEvent(event);
        }
      }
    );

    await PushNotifications.register();
    initialized = true;
  } catch (err) {
    console.error("[Push] Init failed:", err);
  }
}

/**
 * Unregister push notifications. Call on logout so the backend stops
 * sending pushes to this device. Silently no-ops on web or if no token
 * was registered during this session.
 */
export async function unregisterPushNotifications(): Promise<void> {
  if (Capacitor.getPlatform() === "web") return;
  if (!currentFcmToken) return;
  try {
    await api.post("/notifications/unregister", { token: currentFcmToken });
    currentFcmToken = null;
  } catch (err) {
    console.error("[Push] Failed to unregister token:", err);
  }
}