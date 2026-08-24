"use client";

/**
 * MOB-P2-001: Push Notifications Service - End to End
 *
 * FCM token registration with the backend (MOB-P1-001), deep-link
 * navigation (MOB-P1-009) and foreground display via local notifications.
 */

import { Capacitor } from "@capacitor/core";
import { api } from "@/app/services/api/client";

const NOTIFICATION_CHANNEL_ID = "aibusiness_default";

let initialized = false;
let currentFcmToken: string | null = null;

/**
 * MOBILE-HARDENING #5: handles de listeners activos para poder removerlos
 * antes de un re-registro (evita duplicados si initPushNotifications()
 * se ejecuta más de una vez, p. ej. re-login tras logout).
 */
type ListenerHandle = { remove: () => Promise<void> };
let pushListenerHandles: ListenerHandle[] = [];

/**
 * MOBILE-HARDENING #5: los IDs de LocalNotifications deben ser enteros
 * válidos (int32 en Android). Number.parseInt puede dar NaN y Date.now()
 * crudo excede el rango int32 (≈2.1e9), así que se normaliza por módulo.
 */
function toValidNotificationId(rawId?: string): number {
  const parsed = rawId ? Number.parseInt(rawId, 10) : Number.NaN;
  const base = Number.isInteger(parsed) && !Number.isNaN(parsed) ? parsed : Date.now();
  return Math.abs(base % 2147483647);
}

/**
 * Initialize push notifications. Call once at app startup.
 * Silently no-ops on web or if plugin is not installed.
 */
export async function initPushNotifications(): Promise<void> {
  if (initialized) return;
  if (!Capacitor.isNativePlatform()) return;

  try {
    await createNotificationChannel();

    const { PushNotifications } = await import("@capacitor/push-notifications");
    const permission = await PushNotifications.requestPermissions();
    if (permission.receive !== "granted") {
      console.warn("[Push] Permission denied");
      return;
    }

    await registerPushListeners();
    await PushNotifications.register();
    // MOBILE-HARDENING #5: nunca loguear el valor del token FCM.
    console.log("[Push] Registration initiated");
    initialized = true;
  } catch (err) {
    console.error("[Push] Init failed:", err);
  }
}

async function createNotificationChannel(): Promise<void> {
  try {
    const { LocalNotifications } = await import("@capacitor/local-notifications");
    await LocalNotifications.createChannel({
      id: NOTIFICATION_CHANNEL_ID,
      name: "Notificaciones AI Business",
      description: "Notificaciones de oportunidades, alertas y actualizaciones",
      importance: 4,
      visibility: 1,
      vibration: true,
      sound: "default",
    });
  } catch (err) {
    console.warn("[Push] Channel creation failed:", err);
  }
}

async function registerPushListeners(): Promise<void> {
  const { PushNotifications } = await import("@capacitor/push-notifications");

  // MOBILE-HARDENING #5: deduplicación. Si ya había listeners de una
  // invocación previa, se remueven antes de registrar los nuevos.
  await Promise.all(
    pushListenerHandles.splice(0).map((h) => h.remove().catch(() => undefined))
  );

  const registrationHandle = await PushNotifications.addListener(
    "registration",
    async (token: { value: string }) => {
      currentFcmToken = token.value;
      // MOBILE-HARDENING #5: el valor del token NUNCA va a logs (ni en
      // producción ni en desarrollo): es una credencial que permite enviar
      // push al dispositivo.
      console.log("[Push] FCM token recibido y enviado al backend");
      try {
        await api.post("/notifications/register", {
          token: token.value,
          platform: Capacitor.getPlatform(),
        });
      } catch (err) {
        console.error("[Push] Token registration failed:", err);
      }
    }
  );
  pushListenerHandles.push(registrationHandle);

  const errorHandle = await PushNotifications.addListener(
    "registrationError",
    (err: { error?: string }) => {
      console.error("[Push] Registration error:", err.error);
    }
  );
  pushListenerHandles.push(errorHandle);

  const receivedHandle = await PushNotifications.addListener(
    "pushNotificationReceived",
    async (notification: { title?: string; body?: string; id?: string; data?: Record<string, unknown> }) => {
      // MOBILE-HARDENING #5: no volcar el payload completo (puede contener
      // datos sensibles); basta con el título para diagnóstico.
      console.log("[Push] Foreground notification:", notification.title ?? "(sin título)");
      await showForegroundNotification(notification);
    }
  );
  pushListenerHandles.push(receivedHandle);

  const actionHandle = await PushNotifications.addListener(
    "pushNotificationActionPerformed",
    (action: { notification: { data?: Record<string, unknown> } }) => {
      console.log("[Push] Notification tapped");
      handleNotificationTap(action.notification.data);
    }
  );
  pushListenerHandles.push(actionHandle);
}

async function showForegroundNotification(notification: {
  title?: string;
  body?: string;
  id?: string;
  data?: Record<string, unknown>;
}): Promise<void> {
  try {
    const { LocalNotifications } = await import("@capacitor/local-notifications");
    await LocalNotifications.schedule({
      notifications: [
        {
          title: notification.title || "AI Business Platform",
          body: notification.body || "Nueva notificacion",
          id: toValidNotificationId(notification.id),
          channelId: NOTIFICATION_CHANNEL_ID,
          extra: notification.data || {},
          smallIcon: "ic_stat_icon_config_sample",
          autoCancel: true,
        },
      ],
    });
  } catch (err) {
    console.error("[Push] Foreground display failed:", err);
  }
}

function handleNotificationTap(data?: Record<string, unknown>): void {
  if (!data) return;
  if (data.deepLink && typeof data.deepLink === "string") {
    const event = new CustomEvent("deepLink:navigate", { detail: { url: data.deepLink } });
    window.dispatchEvent(event);
  }
  if (data.type) handleNotificationByType(String(data.type), data);
}

function handleNotificationByType(type: string, data: Record<string, unknown>): void {
  switch (type) {
    case "opportunity":
      if (data.opportunityId) {
        window.dispatchEvent(
          new CustomEvent("deepLink:navigate", {
            detail: { url: `aibusiness://opportunity/${data.opportunityId}` },
          })
        );
      }
      break;
    case "deal":
      if (data.dealId) {
        window.dispatchEvent(
          new CustomEvent("deepLink:navigate", {
            detail: { url: `aibusiness://deal/${data.dealId}` },
          })
        );
      }
      break;
    default:
      console.log("[Push] Unknown type:", type);
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

/**
 * MOBILE-HARDENING #5: teardown completo al cerrar sesión. Remueve listeners,
 * limpia el estado y resetea `initialized` para que un próximo login pueda
 * volver a inicializar sin duplicar nada.
 */
export async function teardownPushNotifications(): Promise<void> {
  await unregisterPushNotifications();
  if (pushListenerHandles.length > 0) {
    const handles = pushListenerHandles.splice(0);
    await Promise.all(handles.map((h) => h.remove().catch(() => undefined)));
  }
  currentFcmToken = null;
  initialized = false;
}
