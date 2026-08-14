"use client";

/**
 * MOB-P2-006: Notification Navigation Service
 */

import { useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Capacitor } from "@capacitor/core";
import { useDeepLinks, parseDeepLink, resolveDeepLinkRoute } from "@/app/hooks/use-deep-links";

export function useNotificationNavigation() {
  const router = useRouter();
  useDeepLinks();

  const navigateFromNotification = useCallback(
    (url: string) => {
      const data = parseDeepLink(url);
      if (!data) {
        console.warn("[NotificationNav] Invalid:", url);
        return;
      }
      const route = resolveDeepLinkRoute(data);
      if (route) router.push(route);
    },
    [router]
  );

  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;
    const handler = (e: Event) => {
      const customEvent = e as CustomEvent<{ url: string }>;
      if (customEvent.detail?.url) navigateFromNotification(customEvent.detail.url);
    };
    window.addEventListener("deepLink:navigate", handler);
    return () => window.removeEventListener("deepLink:navigate", handler);
  }, [navigateFromNotification]);

  return { navigateFromNotification };
}

export function NotificationNavigator({ children }: { children: React.ReactNode }) {
  useNotificationNavigation();
  return <>{children}</>;
}
