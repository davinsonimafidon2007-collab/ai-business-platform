"use client";

import { toastError, toastWarning } from "@/app/store/toast";

interface ApiError {
  status: number;
  message: string;
  code?: string;
  retryAfter?: number;
}

export function parseApiError(error: unknown): ApiError {
  if (error instanceof Response) {
    return {
      status: error.status,
      message: getStatusMessage(error.status),
      retryAfter: parseInt(error.headers.get("Retry-After") || "0"),
    };
  }

  if (error instanceof Error) {
    if (error.message.includes("fetch")) {
      return { status: 0, message: "No se pudo conectar con el servidor. Verifica tu conexión." };
    }
    return { status: 500, message: error.message };
  }

  return { status: 500, message: "Error desconocido" };
}

function getStatusMessage(status: number): string {
  const messages: Record<number, string> = {
    400: "Solicitud inválida. Verifica los datos enviados.",
    401: "Sesión expirada. Inicia sesión de nuevo.",
    403: "No tienes permisos para realizar esta acción.",
    404: "Recurso no encontrado.",
    409: "Conflicto. El recurso ya existe o hay una operación en curso.",
    422: "Datos inválidos. Corrige los errores e intenta de nuevo.",
    429: "Demasiadas solicitudes. Espera un momento e intenta de nuevo.",
    500: "Error interno del servidor. Intenta más tarde.",
    502: "Servicio no disponible. El servidor está en mantenimiento.",
    503: "Servicio sobrecargado. Intenta de nuevo en unos minutos.",
  };
  return messages[status] || `Error ${status}: Algo salió mal.`;
}

export function handleApiError(error: unknown, context?: string) {
  const apiError = parseApiError(error);

  if (apiError.status === 429 && apiError.retryAfter) {
    toastWarning(
      "Rate limit alcanzado",
      `Demasiadas solicitudes. Espera ${apiError.retryAfter} segundos e intenta de nuevo.`
    );
    return;
  }

  if (apiError.status === 401) {
    toastError("Sesión expirada", "Tu sesión ha caducado. Inicia sesión de nuevo.");
    return;
  }

  toastError(
    context ? `Error: ${context}` : "Error",
    apiError.message
  );
}

export function isRetryableError(error: unknown): boolean {
  const apiError = parseApiError(error);
  return [0, 500, 502, 503, 504].includes(apiError.status);
}
