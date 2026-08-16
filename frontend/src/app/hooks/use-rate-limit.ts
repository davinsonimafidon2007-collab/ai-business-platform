"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * useRateLimit — lee los headers ``X-RateLimit-*`` de cualquier respuesta HTTP,
 * persiste el estado en localStorage y expone una cuenta regresiva hasta que
 * se restablece el límite (para mostrar en el toast de rate-limit).
 *
 * Contrato de headers (los emite el backend FastAPI + rate_limit_middleware):
 *   - ``X-RateLimit-Limit``      → cuota total del periodo
 *   - ``X-RateLimit-Remaining``  → peticiones restantes en el periodo
 *   - ``X-RateLimit-Reset``      → epoch ms (unix * 1000) de reset
 *   - ``X-RateLimit-Retry-After``→ segundos hasta poder reintentar (429)
 *
 * El hook expone:
 *   - ``remaining`` / ``limit``  → cuota restante y total.
 *   - ``low``                    → true cuando quedan <= 5 peticiones.
 *   - ``retryAfterMs``           → ms restantes hasta el reset (para 429).
 *   - ``tooMany``                → true tras recibir un 429.
 *   - ``checkResponse``          → call a llamar con el Response del fetch.
 */

const RATE_LIMIT_STORAGE_KEY = "abp_rate_limit";
const LOW_THRESHOLD = 5;

export interface RateLimitState {
  limit: number | null;
  remaining: number | null;
  resetAt: number | null; // epoch ms
}

export interface UseRateLimitResult {
  remaining: number | null;
  limit: number | null;
  low: boolean;
  retryAfterMs: number;
  tooMany: boolean;
  checkResponse: (res: Response) => void;
}

function readStored(): RateLimitState {
  if (typeof window === "undefined") return { limit: null, remaining: null, resetAt: null };
  try {
    const raw = localStorage.getItem(RATE_LIMIT_STORAGE_KEY);
    return raw
      ? (JSON.parse(raw) as RateLimitState)
      : { limit: null, remaining: null, resetAt: null };
  } catch {
    return { limit: null, remaining: null, resetAt: null };
  }
}

function parseHeaderInt(value: string | null): number | null {
  if (!value) return null;
  const n = parseInt(value, 10);
  return Number.isFinite(n) ? n : null;
}

export function useRateLimit(): UseRateLimitResult {
  const [state, setState] = useState<RateLimitState>(readStored);
  const [tooMany, setTooMany] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  // Tick de 1s para recalcular la cuenta regresiva del retry.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const persist = useCallback((next: RateLimitState) => {
    setState(next);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(RATE_LIMIT_STORAGE_KEY, JSON.stringify(next));
      } catch {
        // localStorage lleno/bloqueado → no persistir, no fallar
      }
    }
  }, []);

  const checkResponse = useCallback(
    (res: Response) => {
      if (!res || typeof res.status !== "number") return;

      const header = (k: string) => res.headers?.get(k);

      const limit = parseHeaderInt(header("x-ratelimit-limit"));
      const remaining = parseHeaderInt(header("x-ratelimit-remaining"));
      let resetAt: number | null = null;

      if (header("x-ratelimit-reset")) {
        // El backend devuelve epoch ms. Si viniera en segundos (< 1e12),
        // lo normalizamos a ms.
        const raw = parseHeaderInt(header("x-ratelimit-reset"));
        if (raw != null) resetAt = raw < 1e12 ? raw * 1000 : raw;
      }

      if (limit != null || remaining != null || resetAt != null) {
        persist({ limit, remaining, resetAt });
      }

      // 429 → agotado. Retry-After (segundos) o diferencia con resetAt.
      if (res.status === 429) {
        setTooMany(true);
        const retryAfter = parseHeaderInt(header("x-ratelimit-retry-after"));
        const resume =
          retryAfter != null
            ? Date.now() + retryAfter * 1000
            : resetAt ?? Date.now() + 60 * 1000;
        persist({
          limit,
          remaining: 0,
          resetAt: resume,
        });
      } else {
        setTooMany(false);
      }
    },
    [persist]
  );

  const remaining = state.remaining;
  const low = remaining != null && remaining >= 0 && remaining <= LOW_THRESHOLD;

  const retryAfterMs = state.resetAt ? Math.max(0, state.resetAt - now) : 0;

  return { remaining, limit: state.limit, low, retryAfterMs, tooMany, checkResponse };
}