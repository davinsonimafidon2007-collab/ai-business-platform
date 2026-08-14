"use client";

import React from "react";
import { X } from "lucide-react";
import { useAppUpdate } from "@/app/hooks/use-app-update";

/**
 * AppUpdateBanner — banner flotante de actualización de la app móvil.
 *
 * - Estado ``required`` (la versión instalada < min): banner rojo, bloquee la
 *   navegación con un botón de actualización; no se puede descartar.
 * - Estado ``recommended`` (versión instalada < latest): banner ámbar con
 *   botón "Actualizar ahora" y cierre manual (dismiss).
 * - Estado ``up-to-date`` / ``unknown`` / ``loading``: no renderiza nada.
 *
 * Se integra colocándose en el layout raíz de la app.
 */
export function AppUpdateBanner() {
  const { info, status, dismissed, dismiss } = useAppUpdate();

  if (status === "loading" || status === "up-to-date" || status === "unknown") {
    return null;
  }
  if (status === "recommended" && dismissed) {
    return null;
  }

  const isRequired = status === "required";
  const updateUrl = info?.update_url || "#";

  const palette = isRequired
    ? "border-red-200 bg-red-50 text-red-800"
    : "border-amber-200 bg-amber-50 text-amber-800";
  const buttonClass = isRequired
    ? "bg-red-600 text-white hover:bg-red-700"
    : "bg-amber-600 text-white hover:bg-amber-700";

  return (
    <div
      role="alert"
      className={`fixed bottom-4 left-1/2 z-50 flex w-[calc(100%-2rem)] max-w-md -translate-x-1/2 flex-col gap-3 rounded-xl border p-4 shadow-lg ${palette}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-1">
          <p className="text-sm font-semibold">
            {isRequired
              ? "Versión desactualizada"
              : "Actualización disponible"}
          </p>
          <p className="text-xs opacity-80">
            {isRequired
              ? "Debes actualizar la app para continuar usándola con normalidad."
              : `Hay una nueva versión (v${info?.latest_version ?? "?"}). ¡Actualiza para no perderte las últimas mejoras!`}
          </p>
        </div>
        {!isRequired && (
          <button
            onClick={dismiss}
            aria-label="Cerrar aviso"
            className="rounded-md p-1 transition-colors hover:bg-amber-100"
          >
            <X size={16} />
          </button>
        )}
      </div>

      <a
        href={updateUrl}
        target="_blank"
        rel="noopener noreferrer"
        className={`inline-flex h-9 items-center justify-center rounded-lg px-4 text-sm font-medium transition-colors ${buttonClass}`}
      >
        Update now
      </a>
    </div>
  );
}