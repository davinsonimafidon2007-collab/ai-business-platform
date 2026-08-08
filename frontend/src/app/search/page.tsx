"use client";

import { useState } from "react";
import { SearchFilters } from "@/app/features/search/SearchFilters";
import { VehicleTable } from "@/app/features/vehicle/VehicleTable";
import { VehicleDrawer } from "@/app/features/vehicle/VehicleDrawer";
import { useSearchVehicles, formatFiltersForApi } from "@/app/hooks/use-search";
import type { SearchFilters as SearchFiltersType, SearchResultItem } from "@/app/types/vehicle";

function searchErrorMessage(err: unknown): { title: string; detail: string; hint?: string } {
  const raw = err instanceof Error ? err.message : String(err ?? "");
  const lower = raw.toLowerCase();

  if (lower.includes("401") || lower.includes("unauthorized") || lower.includes("not authenticated")) {
    return {
      title: "Sesión no válida",
      detail: "No estás autenticado o el token caducó.",
      hint: "Vuelve a iniciar sesión e intenta la búsqueda otra vez.",
    };
  }
  if (lower.includes("403") || lower.includes("forbidden")) {
    return {
      title: "Sin permiso",
      detail: "Tu usuario no tiene permiso para buscar.",
      hint: "Si crees que es un error, contacta a un administrador.",
    };
  }
  if (lower.includes("network") || lower.includes("fetch") || lower.includes("failed to fetch")) {
    return {
      title: "Error de red",
      detail: "No se pudo contactar con el servidor.",
      hint: "Comprueba que la API está en marcha y tu conexión.",
    };
  }
  if (lower.includes("500") || lower.includes("internal")) {
    return {
      title: "Error del servidor",
      detail: raw || "Error interno al buscar.",
      hint: "Revisa logs del backend o el estado en Admin.",
    };
  }
  return {
    title: "Error al buscar",
    detail: raw || "No se pudo completar la búsqueda.",
  };
}

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

      {/* Provider Issues Warning (SEARCH.DIAG.1) */}
      {searchMutation.isSuccess && (searchMutation.data.provider_issues?.length ?? 0) > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-900/20">
          <h3 className="text-sm font-semibold text-amber-700 dark:text-amber-300">
            Algunos providers no respondieron
          </h3>
          <ul className="mt-2 space-y-1 text-sm text-amber-600 dark:text-amber-400">
            {searchMutation.data.provider_issues?.map((issue, idx) => (
              <li key={`${issue.provider}-${idx}`}>
                <span className="font-medium">{issue.provider}</span>:{" "}
                {issue.message_es || issue.message}
              </li>
            ))}
          </ul>
        </div>
      )}

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
      {searchMutation.isError && (() => {
        const copy = searchErrorMessage(searchMutation.error);
        return (
          <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-900/20">
            <h3 className="text-lg font-semibold text-red-700 dark:text-red-300">{copy.title}</h3>
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">{copy.detail}</p>
            {copy.hint && (
              <p className="mt-3 text-xs text-red-500/90 dark:text-red-400/80">{copy.hint}</p>
            )}
          </div>
        );
      })()}

      {/* Empty State */}
      {searchMutation.isSuccess && searchMutation.data.results.length === 0 && (
        <div className="rounded-lg border border-secondary-200 p-12 text-center dark:border-secondary-700">
          <p className="text-4xl" aria-hidden>🔍</p>
          <h3 className="mt-4 text-lg font-semibold text-secondary-900 dark:text-secondary-100">
            Sin resultados
          </h3>
          <p className="mt-2 text-sm text-secondary-500 dark:text-secondary-400">
            No se encontraron vehículos con esos filtros.
          </p>
          <ul className="mx-auto mt-4 max-w-md list-inside list-disc text-left text-sm text-secondary-500 dark:text-secondary-400">
            <li>Prueba otra marca, modelo o rango de precio.</li>
            <li>Amplía el presupuesto o quita filtros estrictos.</li>
            <li>
              Si siempre sale vacío, revisa el estado de los providers en{" "}
              <a href="/admin" className="font-medium text-primary-600 underline dark:text-primary-400">
                Admin
              </a>{" "}
              (mobile.de puede estar bloqueado sin proxy; AutoScout24 debería responder).
            </li>
          </ul>
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