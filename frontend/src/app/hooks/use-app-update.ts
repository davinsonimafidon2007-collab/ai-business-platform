"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchAppUpdate,
  type MobileVersionInfo,
  type UpdateStatus,
} from "@/app/services/app-update";

/**
 * useAppUpdate — hook de polling que consulta el estado de actualización de la
 * app cada ``POLL_INTERVAL_MS`` (6h por defecto) y expone un flag ``dismissed``
 * para que la UI pueda ocultar el banner sin perder el estado.
 *
 * Comportamiento:
 *   - Arranca a los ``INITIAL_DELAY_MS`` (evita el fetch en el primer frame).
 *   - Re-consulta cada 6h.
 *   - Si el estado es ``required`` (obligatorio) el banner NO se puede
 *     descartar de forma persistente (se vuelve a mostrar).
 *   - Expone ``checkNow`` por si la API lo necesita bajo demanda.
 */

const POLL_INTERVAL_MS = 6 * 60 * 60 * 1000; // 6 horas
const INITIAL_DELAY_MS = 2000;

export interface UseAppUpdateResult {
  /** Info de versión más reciente (o null antes del primer fetch). */
  info: MobileVersionInfo | null;
  /** Último estado derivado. */
  status: UpdateStatus | "loading";
  /** true si el usuario descartó el banner (en estados no obligatorios). */
  dismissed: boolean;
  /** Oculta el banner. No surte efecto si el estado es ``required``. */
  dismiss: () => void;
  /** Fuerza una comprobación inmediata. */
  checkNow: () => Promise<void>;
}

export function useAppUpdate(): UseAppUpdateResult {
  const [info, setInfo] = useState<MobileVersionInfo | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const checkNow = useCallback(async () => {
    try {
      const result = await fetchAppUpdate();
      setInfo(result);
      // Un cambio a "required" desbloquea el banner aunque esté descartado.
      if (result.status === "required") {
        setDismissed(false);
      }
    } catch {
      // fetchAppUpdate ya degrada a "unknown"; no propagar aquí.
    }
  }, []);

  useEffect(() => {
    const start = setTimeout(() => {
      void checkNow();
      intervalRef.current = setInterval(() => void checkNow(), POLL_INTERVAL_MS);
    }, INITIAL_DELAY_MS);

    return () => {
      clearTimeout(start);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [checkNow]);

  const dismiss = useCallback(() => {
    // Un update obligatorio no se puede ocultar de forma persistente.
    if (info?.status === "required") return;
    setDismissed(true);
  }, [info?.status]);

  const status: UpdateStatus | "loading" = info?.status ?? "loading";

  return { info, status, dismissed, dismiss, checkNow };
}
