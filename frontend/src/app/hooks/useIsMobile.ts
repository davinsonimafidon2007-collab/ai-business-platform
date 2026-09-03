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
  // Bug real de hidratación: leer window.matchMedia() en el inicializador
  // de useState corre también durante la hidratación en cliente (no solo
  // en re-renders), donde `window` ya existe — a diferencia del render en
  // servidor, donde siempre es `undefined`. Con viewport móvil real, el
  // servidor renderiza el shell de escritorio (Sidebar/Navbar) y el cliente
  // hidrata directamente con el shell móvil (bottom tabs): árboles DOM
  // distintos → React descarta el HTML del servidor con el error de
  // hidratación #418 en cada carga de página. El estado inicial debe ser
  // determinista (igual que el servidor); el valor real se aplica en
  // useEffect, que solo corre tras la hidratación.
  const [mobile, setMobile] = useState<boolean>(false);

  useEffect(() => {
    if (isNative()) {
      setMobile(true);
      return;
    }

    const mq = window.matchMedia(`(max-width: ${breakpointPx - 1}px)`);
    const apply = () => setMobile(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [breakpointPx]);

  return mobile;
}