"use client";

/**
 * MOB-P1-001: Push notifications service for Capacitor.
 *
 * This module provides:
 * - Registration of FCM tokens with the backend
 * - Permission request for notifications
 * - Handling notification received / clicked events
 *
 * Requires: @capacitor/push-notifications plugin
 *
 * Usage in app/providers.tsx:
 *   import { initPushNotifications } from "@/app/services/push-notifications";
 *   useEffect(() => { initPushNotifications(); }, []);
 */

import { Capacitor } from "@capacitor/core";
import { api } from "@/app/services/api/client";

let initialized = false;

/**
 * Initialize push notifications. Call once at app startup.
 * Silently no-ops on web or if plugin is not installed.
 */
export async function initPushNotifications(): Promise<void> {
  if (initialized) return;
  if (Capacitor.getPlatform() === "web") return;

  try {
    // Dynamic import to avoid issues on web
    // @ts-expect-error — plugin may not be installed; runtime guard via try/catch
    const { PushNotifications } = await import("@capacitor/push-notifications");

    // Request permission
    const permission = await PushNotifications.requestPermissions();
    if (permission.receive !== "granted") {
      console.warn("Push notification permission not granted");
      return;
    }

    // Register for push
    await PushNotifications.register();

    // Listen for registration
    PushNotifications.addListener("registration", async (token: { value: string }) => {
      try {
        await api.post("/notifications/register", { token: token.value });
      } catch (err) {
        console.error("Failed to register push token:", err);
      }
    });

    // Listen for registration errors
    PushNotifications.addListener("registrationError", (error: Error) => {
      console.error("Push registration error:", error);
    });

    // Listen for received notifications (app in foreground)
    PushNotifications.addListener("pushNotificationReceived", (notification: { title?: string; body?: string }) => {
      console.log("Push received:", notification.title, notification.body);
    });

    // Listen for notification opened (tap)
    PushNotifications.addListener("pushNotificationActionPerformed", (action: { notification: { data?: { url?: string } } }) => {
      const data = action.notification.data;
      if (data?.url) {
        window.location.href = data.url;
      }
    });

    initialized = true;
  } catch (err) {
    // Plugin not installed or not available — silent fail
    console.warn("Push notifications not available:", err);
  }
}
