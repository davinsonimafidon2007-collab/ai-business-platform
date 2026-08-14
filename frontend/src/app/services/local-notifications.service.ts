"use client";

/**
 * MOB-P2-005: Local Notifications Service
 */

import { Capacitor } from "@capacitor/core";

export interface ReminderConfig {
  dealId: string;
  dealTitle: string;
  reminderType: "follow_up" | "price_drop" | "deadline" | "custom";
  scheduledAt: Date;
  message?: string;
}

const CHANNEL_DEALS = "aibusiness_deals";
const CHANNEL_OPPORTUNITIES = "aibusiness_opportunities";
const CHANNEL_REMINDERS = "aibusiness_reminders";

export async function initLocalNotifications(): Promise<void> {
  if (!Capacitor.isNativePlatform()) return;
  try {
    const { LocalNotifications } = await import("@capacitor/local-notifications");
    await LocalNotifications.createChannel({
      id: CHANNEL_DEALS,
      name: "Tratos y Negociaciones",
      description: "Recordatorios de seguimiento",
      importance: 4,
      visibility: 1,
      vibration: true,
    });
    await LocalNotifications.createChannel({
      id: CHANNEL_OPPORTUNITIES,
      name: "Oportunidades",
      description: "Alertas de oportunidades",
      importance: 5,
      visibility: 1,
      vibration: true,
      sound: "default",
    });
    await LocalNotifications.createChannel({
      id: CHANNEL_REMINDERS,
      name: "Recordatorios",
      description: "Recordatorios personalizados",
      importance: 3,
      visibility: 0,
      vibration: false,
    });
    console.log("[LocalNotifications] Channels created");
  } catch (err) {
    console.error("[LocalNotifications] Init failed:", err);
  }
}

export async function scheduleDealReminder(config: ReminderConfig): Promise<void> {
  if (!Capacitor.isNativePlatform()) return;
  try {
    const { LocalNotifications } = await import("@capacitor/local-notifications");
    const notificationId =
      Number.parseInt(config.dealId.replace(/\D/g, "").slice(0, 9), 10) || Date.now();
    await LocalNotifications.schedule({
      notifications: [
        {
          id: notificationId,
          title: getReminderTitle(config.reminderType),
          body: config.message || `Recordatorio: ${config.dealTitle}`,
          channelId: CHANNEL_DEALS,
          schedule: { at: config.scheduledAt },
          extra: {
            type: "deal_reminder",
            dealId: config.dealId,
            deepLink: `aibusiness://deal/${config.dealId}`,
          },
          smallIcon: "ic_stat_icon_config_sample",
          autoCancel: true,
        },
      ],
    });
    console.log("[LocalNotifications] Reminder scheduled:", config.dealId);
  } catch (err) {
    console.error("[LocalNotifications] Schedule failed:", err);
  }
}

export async function scheduleOpportunityAlert(
  opportunityId: string,
  title: string,
  expiresAt: Date
): Promise<void> {
  if (!Capacitor.isNativePlatform()) return;
  try {
    const { LocalNotifications } = await import("@capacitor/local-notifications");
    const alertTime = new Date(expiresAt.getTime() - 24 * 60 * 60 * 1000);
    await LocalNotifications.schedule({
      notifications: [
        {
          id: Number.parseInt(opportunityId.replace(/\D/g, "").slice(0, 9), 10) || Date.now(),
          title: "¡Oportunidad por expirar!",
          body: `"${title}" expira pronto.`,
          channelId: CHANNEL_OPPORTUNITIES,
          schedule: { at: alertTime },
          extra: {
            type: "opportunity_expiring",
            opportunityId,
            deepLink: `aibusiness://opportunity/${opportunityId}`,
          },
          smallIcon: "ic_stat_icon_config_sample",
        },
      ],
    });
  } catch (err) {
    console.error("[LocalNotifications] Opportunity alert failed:", err);
  }
}

export async function cancelDealReminder(dealId: string): Promise<void> {
  if (!Capacitor.isNativePlatform()) return;
  try {
    const { LocalNotifications } = await import("@capacitor/local-notifications");
    await LocalNotifications.cancel({
      notifications: [{ id: Number.parseInt(dealId.replace(/\D/g, "").slice(0, 9), 10) }],
    });
  } catch (err) {
    console.error("[LocalNotifications] Cancel failed:", err);
  }
}

export async function cancelAllReminders(): Promise<void> {
  if (!Capacitor.isNativePlatform()) return;
  try {
    const { LocalNotifications } = await import("@capacitor/local-notifications");
    await LocalNotifications.cancel({ notifications: [] });
  } catch (err) {
    console.error("[LocalNotifications] Cancel all failed:", err);
  }
}

function getReminderTitle(type: string): string {
  switch (type) {
    case "follow_up":
      return "Seguimiento";
    case "price_drop":
      return "Precio reducido";
    case "deadline":
      return "Fecha límite";
    default:
      return "Recordatorio";
  }
}
