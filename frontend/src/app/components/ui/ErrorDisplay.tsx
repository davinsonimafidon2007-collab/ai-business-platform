"use client";

import { Button } from "@/app/components/ui/button";

function classifyError(err: unknown): { title: string; detail: string; hint?: string } {
  const raw = err instanceof Error ? err.message : String(err ?? "");
  const lower = raw.toLowerCase();

  if (lower.includes("401") || lower.includes("unauthorized") || lower.includes("not authenticated")) {
    return {
      title: "Sesión no válida",
      detail: "No estás autenticado o el token caducó.",
      hint: "Vuelve a iniciar sesión e intenta de nuevo.",
    };
  }
  if (lower.includes("403") || lower.includes("forbidden")) {
    return {
      title: "Sin permiso",
      detail: "Tu usuario no tiene permiso para realizar esta acción.",
      hint: "Contacta a un administrador si crees que es un error.",
    };
  }
  if (lower.includes("network") || lower.includes("fetch") || lower.includes("failed to fetch") || lower.includes("econnrefused")) {
    return {
      title: "Error de red",
      detail: "No se pudo contactar con el servidor.",
      hint: "Comprueba que la API está en marcha y tu conexión. Si estás en un dispositivo físico, verifica la URL en Configuración.",
    };
  }
  if (lower.includes("500") || lower.includes("internal")) {
    return {
      title: "Error del servidor",
      detail: raw || "Error interno del servidor.",
      hint: "Revisa los logs del backend o el estado en Admin.",
    };
  }
  return {
    title: "Error",
    detail: raw || "No se pudo completar la operación.",
    hint: "Inténtalo de nuevo más tarde.",
  };
}

interface ErrorDisplayProps {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}

export function ErrorDisplay({ error, onRetry, className }: ErrorDisplayProps) {
  const copy = classifyError(error);

  return (
    <div className={`rounded-lg border border-red-200 bg-red-50 p-4 text-center dark:border-red-800 dark:bg-red-900/20 ${className ?? ""}`}>
      <h3 className="text-sm font-semibold text-red-700 dark:text-red-300">{copy.title}</h3>
      <p className="mt-1 text-sm text-red-600 dark:text-red-400">{copy.detail}</p>
      {copy.hint && (
        <p className="mt-2 text-xs text-red-500/90 dark:text-red-400/80">{copy.hint}</p>
      )}
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-3" onClick={onRetry}>
          Reintentar
        </Button>
      )}
    </div>
  );
}
