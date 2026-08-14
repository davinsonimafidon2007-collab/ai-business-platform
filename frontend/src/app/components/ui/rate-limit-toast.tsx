"use client";

import React from "react";
import { useRateLimit } from "@/app/hooks/use-rate-limit";

/**
 * RateLimitToast — toast flotante que avisa cuando quedan pocas peticiones o
 * cuando el backend responde 429 (límite agotado).
 *
 * - Quedan <= 5 peticiones   → aviso ámbar con la cuota restante.
 * - 429 (tooMany)            → aviso rojo con cuenta regresiva hasta el retry.
 *
 * El hook se integra con cualquier fetch pasándole la respuesta por
 * ``checkResponse(res)`` (ver cliente HTTP).
 */
export function RateLimitToast() {
  const { remaining, limit, low, retryAfterMs, tooMany } = useRateLimit();

  if (!low && !tooMany) {
    return null;
  }

  const isLimit = tooMany;
  const palette = isLimit
    ? "border-red-200 bg-red-50 text-red-800"
    : "border-amber-200 bg-amber-50 text-amber-800";

  const countdown = Math.ceil(retryAfterMs / 1000);

  return (
    <div
      role="status"
      className={`fixed bottom-16 left-1/2 z-50 flex w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 items-center justify-between gap-3 rounded-xl border p-3 shadow-lg ${palette}`}
    >
      <div className="flex flex-col gap-0.5">
        <p className="text-sm font-semibold">
          {isLimit ? "Límite de peticiones alcanzado" : "Quedan pocas peticiones"}
        </p>
        <p className="text-xs opacity-80">
          {isLimit
            ? `Vuelve a intentarlo en ${countdown}s.`
            : `${remaining ?? "?"} de ${limit ?? "?"} peticiones restantes.`}
        </p>
      </div>
      <span className={`shrink-0 text-lg font-bold`}>
        {isLimit ? countdown : remaining}
      </span>
    </div>
  );
}