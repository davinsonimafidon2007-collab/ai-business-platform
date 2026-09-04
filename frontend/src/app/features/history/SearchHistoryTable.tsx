"use client";

import { Button } from "@/app/components/ui/button";
import type { SearchHistory } from "@/app/types/vehicle";

interface SearchHistoryTableProps {
  history: SearchHistory[];
  onReRun: (id: string, query: string) => void;
  onDelete: (id: string) => void;
  isDeleting?: boolean;
}

export function SearchHistoryTable({
  history,
  onReRun,
  onDelete,
  isDeleting,
}: SearchHistoryTableProps) {
  if (!history || history.length === 0) {
    return (
      <div className="rounded-lg border border-secondary-200 p-12 text-center dark:border-secondary-700">
        <p className="text-4xl">📋</p>
        <h3 className="mt-4 text-lg font-semibold text-secondary-900 dark:text-secondary-100">
          Sin historial
        </h3>
        <p className="mt-2 text-sm text-secondary-500 dark:text-secondary-400">
          Aún no has realizado ninguna búsqueda. Comienza buscando vehículos.
        </p>
      </div>
    );
  }

  const formatDate = (timestamp: string) =>
    new Date(timestamp).toLocaleDateString("es-ES", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  return (
    <>
      {/* Bug real: la tabla de 5 columnas se cortaba en móvil (viewport
          ~375px vs ~715px de ancho de contenido) — Repetir/Eliminar y la
          columna Duración quedaban fuera de pantalla, con scroll horizontal
          real pero sin ninguna pista visual de que existía. Se añade una
          vista de tarjetas para móvil, igual que Vehículos/Deals. */}
      <div className="space-y-3 sm:hidden">
        {history.map((search) => (
          <div
            key={search.id}
            className="rounded-lg border border-secondary-200 bg-white p-4 dark:border-secondary-700 dark:bg-secondary-900"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium text-secondary-900 dark:text-secondary-100">
                {search.query}
              </p>
              <span className="shrink-0 text-xs text-secondary-500 dark:text-secondary-400">
                {formatDate(search.timestamp)}
              </span>
            </div>
            <p className="mt-1 text-xs text-secondary-500 dark:text-secondary-400">
              {search.results_count} resultados
              {search.execution_time ? ` · ${search.execution_time.toFixed(1)}s` : ""}
            </p>
            <div className="mt-3 flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onReRun(search.id, search.query)}
                className="flex-1"
              >
                Repetir
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDelete(search.id)}
                disabled={isDeleting}
                className="flex-1 text-red-600 hover:text-red-700 dark:text-red-400"
              >
                Eliminar
              </Button>
            </div>
          </div>
        ))}
      </div>

      <div className="hidden overflow-x-auto rounded-lg border border-secondary-200 dark:border-secondary-700 sm:block">
      <table className="min-w-full divide-y divide-secondary-200 dark:divide-secondary-700">
        <thead className="bg-secondary-50 dark:bg-secondary-800">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">
              Fecha
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">
              Consulta
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">
              Resultados
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">
              Duración
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">
              Acciones
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-secondary-200 bg-white dark:divide-secondary-700 dark:bg-secondary-900">
          {history.map((search) => (
            <tr key={search.id} className="hover:bg-secondary-50 dark:hover:bg-secondary-800">
              <td className="whitespace-nowrap px-6 py-4 text-sm text-secondary-600 dark:text-secondary-400">
                {new Date(search.timestamp).toLocaleDateString("es-ES", {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </td>
              <td className="px-6 py-4 text-sm font-medium text-secondary-900 dark:text-secondary-100">
                {search.query}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-secondary-600 dark:text-secondary-400">
                {search.results_count}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-secondary-600 dark:text-secondary-400">
                {search.execution_time ? `${search.execution_time.toFixed(1)}s` : "-"}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-right text-sm">
                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onReRun(search.id, search.query)}
                  >
                    Repetir
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDelete(search.id)}
                    disabled={isDeleting}
                    className="text-red-600 hover:text-red-700 dark:text-red-400"
                  >
                    Eliminar
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </>
  );
}