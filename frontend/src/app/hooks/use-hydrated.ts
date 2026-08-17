"use client";

import { useEffect, useState } from "react";

/**
 * useHydrated — hook seguro para estado solo-cliente.
 *
 * Devuelve `false` durante el primer render (SSR) y `true` justo después de
 * que el componente se haya hidratado en el cliente (via useEffect). Úsalo
 * para diferir lecturas de browser-only APIs (localStorage, matchMedia…)
 * y evitar hydration mismatches:
 *
 *   const isHydrated = useHydrated();
 *   if (!isHydrated) return <Skeleton />;
 *   // Aquí ya es seguro leer localStorage/etc.
 */
export function useHydrated() {
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  return hydrated;
}