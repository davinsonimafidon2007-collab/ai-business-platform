"use client";

import { useEffect, useState } from "react";
import { Capacitor } from "@capacitor/core";

function isNative(): boolean {
  if (typeof window === "undefined") return false;
  return Capacitor.isNativePlatform();
}

/**
 * MOBILE.SHELL.1 — Detecta viewport móvil.
 *
 * Devuelve `true` cuando el ancho es menor a `breakpointPx`, o cuando corre
 * sobre plataforma nativa de Capacitor (así el APK siempre usa el shell móvil,
 * aunque la tablet en landscape sea ancha).
 */
export function useIsMobile(breakpointPx = 768): boolean {
  // Nativo ya resuelto en el inicializador del estado (sin setState en effect).
  const [mobile, setMobile] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    if (isNative()) return true;
    return window.matchMedia(`(max-width: ${breakpointPx - 1}px)`).matches;
  });

  useEffect(() => {
    // En plataforma nativa nunca cambia: se mantiene el valor inicial true.
    if (isNative()) return;

    const mq = window.matchMedia(`(max-width: ${breakpointPx - 1}px)`);
    const apply = () => setMobile(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [breakpointPx]);

  return mobile;
}