"use client";

import React from "react";

interface DataStateAction {
  label: string;
  onClick: () => void;
}

interface EmptyProps {
  icon?: string;
  title: string;
  description?: string;
  action?: DataStateAction;
}

interface DataStateProps<T> {
  isLoading?: boolean;
  isError?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  data?: T | null;
  emptyProps?: EmptyProps;
  children: (data: NonNullable<T>) => React.ReactNode;
}

/**
 * DataState — renderiza el estado de carga/error/vacío/datos para cualquier
 * componente que consuma una fuente asíncrona (React Query, fetch manual).
 *
 * Usa un render-prop (children) para el caso datos existentes, y slots
 * declarativos para los demás estados. Así garantizamos:
 *   - Carga: spinner + texto "Cargando..."
 *   - Error: mensaje + botón "Intentar de nuevo" (con `onRetry`)
 *   - Vacío: icono + título + acción opcional (botón "Create" etc.)
 *   - Datos: renderiza el children con los datos tipados.
 */
export function DataState<T>({
  isLoading,
  isError,
  error,
  onRetry,
  data,
  emptyProps,
  children,
}: DataStateProps<T>) {
  // --- Loading ---
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 p-8 text-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        <p className="text-sm text-secondary-500">Cargando...</p>
      </div>
    );
  }

  // --- Error ---
  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 p-8 text-center">
        <p className="text-sm text-error">
          {error?.message ?? "Algo salió mal"}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center justify-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          >
            Intentar de nuevo
          </button>
        )}
      </div>
    );
  }

  // --- Empty / null / undefined ---
  if (data == null || (Array.isArray(data) && data.length === 0)) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 p-8 text-center">
        {emptyProps?.icon && <span className="text-3xl">{emptyProps.icon}</span>}
        <p className="font-medium text-secondary-900">
          {emptyProps?.title ?? "Sin datos"}
        </p>
        {emptyProps?.description && (
          <p className="text-sm text-secondary-500">{emptyProps.description}</p>
        )}
        {emptyProps?.action && (
          <button
            onClick={emptyProps.action.onClick}
            className="inline-flex items-center justify-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          >
            {emptyProps.action.label}
          </button>
        )}
      </div>
    );
  }

  // --- Data ---
  return <>{children(data)}</>;
}