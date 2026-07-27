"use client";

import { useState } from "react";
import { SearchFilters } from "@/app/features/search/SearchFilters";
import { VehicleTable } from "@/app/features/vehicle/VehicleTable";
import { VehicleDrawer } from "@/app/features/vehicle/VehicleDrawer";
import { useSearchVehicles, formatFiltersForApi } from "@/app/hooks/use-search";
import type { SearchFilters as SearchFiltersType, SearchResultItem } from "@/app/types/vehicle";

export default function SearchPage() {
  const searchMutation = useSearchVehicles();
  const [selectedVehicle, setSelectedVehicle] = useState<SearchResultItem | null>(null);

  const handleSearch = (filters: SearchFiltersType) => {
    const apiParams = formatFiltersForApi(filters);
    searchMutation.mutate(apiParams);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
          Búsqueda de vehículos
        </h1>
        <p className="text-secondary-500 dark:text-secondary-400">
          Encuentra vehículos para importación y analiza su rentabilidad
        </p>
      </div>

      <SearchFilters onSearch={handleSearch} isLoading={searchMutation.isPending} />

      {/* Loading State */}
      {searchMutation.isPending && (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
          <p className="mt-4 text-sm text-secondary-500 dark:text-secondary-400">
            Buscando vehículos...
          </p>
        </div>
      )}

      {/* Error State */}
      {searchMutation.isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-900/20">
          <p className="text-red-600 dark:text-red-400">
            Error al realizar la búsqueda: {searchMutation.error.message}
          </p>
        </div>
      )}

      {/* Empty State */}
      {searchMutation.isSuccess && searchMutation.data.results.length === 0 && (
        <div className="rounded-lg border border-secondary-200 p-12 text-center dark:border-secondary-700">
          <p className="text-4xl">🔍</p>
          <h3 className="mt-4 text-lg font-semibold text-secondary-900 dark:text-secondary-100">
            Sin resultados
          </h3>
          <p className="mt-2 text-sm text-secondary-500 dark:text-secondary-400">
            No se encontraron vehículos con los filtros especificados. Intenta con una búsqueda diferente.
          </p>
        </div>
      )}

      {/* Success State with Summary */}
      {searchMutation.isSuccess && searchMutation.data.results.length > 0 && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <SummaryCard label="Total" value={searchMutation.data.summary.total_results} />
            <SummaryCard label="Excelentes" value={searchMutation.data.summary.excellent} color="text-green-600" />
            <SummaryCard label="Buenas" value={searchMutation.data.summary.good} color="text-blue-600" />
            <SummaryCard label="Medias" value={searchMutation.data.summary.average} color="text-yellow-600" />
            <SummaryCard label="Bajas" value={searchMutation.data.summary.poor} color="text-orange-600" />
            <SummaryCard label="Rechazados" value={searchMutation.data.summary.rejected} color="text-red-600" />
          </div>

          {/* Results Table */}
          <VehicleTable
            vehicles={searchMutation.data.results}
            onSelectVehicle={setSelectedVehicle}
          />
        </>
      )}

      {/* Vehicle Detail Drawer */}
      <VehicleDrawer
        vehicle={selectedVehicle}
        onClose={() => setSelectedVehicle(null)}
      />
    </div>
  );
}

function SummaryCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="rounded-lg border border-secondary-200 bg-white p-3 text-center dark:border-secondary-700 dark:bg-secondary-800">
      <p className="text-xs font-medium text-secondary-500 dark:text-secondary-400">{label}</p>
      <p className={`mt-1 text-xl font-bold ${color || "text-secondary-900 dark:text-secondary-100"}`}>
        {value}
      </p>
    </div>
  );
}