"use client";

/**
 * MobileBootstrap — inicializaciones nativas (Bloque 4).
 *
 * Se monta una sola vez en el RootLayout. En plataforma nativa (Capacitor):
 *  - inicializa Google Auth (plugin @codetrix-studio/capacitor-google-auth),
 *    requisito previo para que signIn() funcione en Android/iOS (MOB-P1-001);
 *  - inicializa push notifications (FCM + channel + listeners, MOB-P2-001).
 *
 * En web no-op (los servicios ya no-op por plataforma), así que es seguro
 * montarlo siempre.
 */

import { useEffect, useRef } from "react";
import { initGoogleAuth } from "@/app/services/google-auth";
import { initPushNotifications } from "@/app/services/push-notifications";

export function MobileBootstrap() {
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    initGoogleAuth();
    void initPushNotifications();
  }, []);

  return null;
}
