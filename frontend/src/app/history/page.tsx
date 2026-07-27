"use client";

import { useRouter } from "next/navigation";
import { useSearchHistory, useDeleteSearch, formatFiltersForApi } from "@/app/hooks/use-search";
import { useSearchVehicles } from "@/app/hooks/use-search";
import { SearchHistoryTable } from "@/app/features/history/SearchHistoryTable";
import { SearchFilters } from "@/app/features/search/SearchFilters";
import { VehicleTable } from "@/app/features/vehicle/VehicleTable";
import { VehicleDrawer } from "@/app/features/vehicle/VehicleDrawer";
import { useState } from "react";
import type { SearchFilters as SearchFiltersType, SearchResultItem } from "@/app/types/vehicle";

export default function HistoryPage() {
  const router = useRouter();
  const { data: history, isLoading, isError, error, refetch } = useSearchHistory();
  const deleteSearch = useDeleteSearch();
  const searchMutation = useSearchVehicles();
  const [selectedVehicle, setSelectedVehicle] = useState<SearchResultItem | null>(null);

  const handleReRun = (id: string, query: string) => {
    // Navigate to search page with the query
    router.push(`/search?query=${encodeURIComponent(query)}`);
  };

  const handleDelete = (id: string) => {
    if (confirm("¿Estás seguro de que deseas eliminar esta búsqueda del historial?")) {
      deleteSearch.mutate(id);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
          Historial de búsquedas
        </h1>
        <p className="text-secondary-500 dark:text-secondary-400">
          Consulta y repite búsquedas anteriores
        </p>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="animate-pulse rounded-lg border border-secondary-200 p-4 dark:border-secondary-700">
              <div className="h-4 w-48 rounded bg-secondary-200 dark:bg-secondary-700" />
              <div className="mt-2 h-3 w-32 rounded bg-secondary-200 dark:bg-secondary-700" />
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-900/20">
          <p className="text-red-600 dark:text-red-400">
            Error al cargar el historial: {error?.message}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-3 text-sm font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400"
          >
            Intentar de nuevo
          </button>
        </div>
      )}

      {/* Success */}
      {!isLoading && !isError && (
        <SearchHistoryTable
          history={history || []}
          onReRun={handleReRun}
          onDelete={handleDelete}
          isDeleting={deleteSearch.isPending}
        />
      )}
    </div>
  );
}