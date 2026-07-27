"use client";

import { useSearchHistory } from "@/app/hooks/use-search";
import { StatCard } from "@/app/components/ui/StatCard";
import { ScoreBadge, OpportunityBadge, RecommendationBadge } from "@/app/components/ui/ScoreBadge";

export default function DashboardPage() {
  const { data: history, isLoading, isError, error } = useSearchHistory();

  // Calculate stats from search history
  const totalSearches = history?.length || 0;
  const totalVehicles = history?.reduce((sum, h) => sum + (h.results_count || 0), 0) || 0;
  const averageResultsPerSearch = totalSearches > 0 ? Math.round(totalVehicles / totalSearches) : 0;

  // Distribution of opportunities from summary (if we had it stored)
  // For now, use search history counts as a proxy

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
          Dashboard
        </h1>
        <p className="text-secondary-500 dark:text-secondary-400">
          Resumen de actividad y oportunidades
        </p>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="animate-pulse rounded-lg border border-secondary-200 bg-white p-4 dark:border-secondary-700 dark:bg-secondary-800">
              <div className="h-4 w-24 rounded bg-secondary-200 dark:bg-secondary-700" />
              <div className="mt-2 h-8 w-16 rounded bg-secondary-200 dark:bg-secondary-700" />
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-600 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
          Error al cargar datos: {error?.message}
        </div>
      )}

      {/* Stats */}
      {!isLoading && !isError && (
        <>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Búsquedas realizadas"
              value={totalSearches}
              icon="🔍"
              trend={totalSearches > 0 ? "up" : "neutral"}
              subtitle={totalSearches > 0 ? "Total acumulado" : "Sin actividad aún"}
            />
            <StatCard
              title="Vehículos analizados"
              value={totalVehicles}
              icon="🚗"
              trend={totalVehicles > 0 ? "up" : "neutral"}
              subtitle={totalVehicles > 0 ? `${averageResultsPerSearch} por búsqueda` : "Sin datos"}
            />
            <StatCard
              title="Oportunidades excelentes"
              value={0}
              icon="⭐"
              subtitle="Pendiente de implementación en backend"
            />
            <StatCard
              title="ROI medio"
              value="—"
              icon="📈"
              subtitle="Pendiente de implementación en backend"
            />
          </div>

          {/* Recent Searches */}
          <div className="rounded-lg border border-secondary-200 bg-white dark:border-secondary-700 dark:bg-secondary-800">
            <div className="border-b border-secondary-200 px-6 py-4 dark:border-secondary-700">
              <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100">
                Actividad reciente
              </h2>
            </div>

            {!history || history.length === 0 ? (
              <div className="p-12 text-center">
                <p className="text-4xl">📋</p>
                <h3 className="mt-4 text-lg font-semibold text-secondary-900 dark:text-secondary-100">
                  Sin actividad
                </h3>
                <p className="mt-2 text-sm text-secondary-500 dark:text-secondary-400">
                  No hay actividad reciente. Comienza realizando una búsqueda.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-secondary-200 dark:divide-secondary-700">
                  <thead className="bg-secondary-50 dark:bg-secondary-800">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">Fecha</th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">Consulta</th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">Resultados</th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">Duración</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-secondary-200 dark:divide-secondary-700">
                    {history.slice(0, 10).map((search) => (
                      <tr key={search.id} className="hover:bg-secondary-50 dark:hover:bg-secondary-800">
                        <td className="whitespace-nowrap px-6 py-3 text-sm text-secondary-600 dark:text-secondary-400">
                          {new Date(search.created_at).toLocaleDateString("es-ES", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </td>
                        <td className="px-6 py-3 text-sm font-medium text-secondary-900 dark:text-secondary-100">
                          {search.query}
                        </td>
                        <td className="whitespace-nowrap px-6 py-3 text-sm text-secondary-600 dark:text-secondary-400">
                          {search.results_count}
                        </td>
                        <td className="whitespace-nowrap px-6 py-3 text-sm text-secondary-600 dark:text-secondary-400">
                          {search.execution_time ? `${search.execution_time.toFixed(1)}s` : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}