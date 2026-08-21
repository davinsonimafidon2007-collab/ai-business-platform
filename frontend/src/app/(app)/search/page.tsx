"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { SearchFilters } from "@/app/features/search/SearchFilters";
import { VehicleTable } from "@/app/features/vehicle/VehicleTable";
import { VehicleDrawer } from "@/app/features/vehicle/VehicleDrawer";
import { useSearchVehicles, formatFiltersForApi } from "@/app/hooks/use-search";
import { searchOrdersService } from "@/app/services/search-orders";
import { SkeletonCard, ErrorState, EmptyState } from "@/components/ui/StateComponents";
import type { CreateSearchOrderRequest, SearchOrder } from "@/app/types/search-orders";
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
  const [backgroundOrder, setBackgroundOrder] = useState<SearchOrder | null>(null);
  const [lastFilters, setLastFilters] = useState<SearchFiltersType | null>(null);
  const searchParams = useSearchParams();
  const lastLaunchedQueryRef = useRef<string>("");

  const backgroundMutation = useMutation({
    mutationFn: (payload: CreateSearchOrderRequest) => searchOrdersService.create(payload),
    onSuccess: (order) => setBackgroundOrder(order),
  });

  const handleSearch = (filters: SearchFiltersType) => {
    setLastFilters(filters);
    const apiParams = formatFiltersForApi(filters);
    searchMutation.mutate(apiParams);
  };

  const handleRetry = () => {
    if (lastFilters) {
      handleSearch(lastFilters);
    }
  };

  const handleBackgroundSearch = (filters: SearchFiltersType) => {
    const payload: CreateSearchOrderRequest = {
      query: filters.query.trim() || "*",
      total_budget: filters.total_budget ?? null,
      filters: {
        brand: filters.brand || undefined,
        model: filters.model || undefined,
        min_year: filters.min_year,
        max_year: filters.max_year,
        min_mileage: filters.min_mileage,
        max_mileage: filters.max_mileage,
        fuel_type: filters.fuel_type || undefined,
        transmission: filters.transmission || undefined,
        provider: filters.provider || undefined,
        max_results: 30,
      },
    };
    backgroundMutation.mutate(payload);
  };

  useEffect(() => {
    const query = searchParams.get("query");
    if (query && query !== lastLaunchedQueryRef.current) {
      lastLaunchedQueryRef.current = query;
      handleSearch({ query });
    }
  }, [searchParams]);

  useEffect(() => {
    lastLaunchedQueryRef.current = searchParams.get("query") || "";
  }, [searchParams]);

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

      <SearchFilters
        onSearch={handleSearch}
        onBackgroundSearch={handleBackgroundSearch}
        isLoading={searchMutation.isPending || backgroundMutation.isPending}
        initialQuery={searchParams.get("query") || undefined}
      />

      {backgroundMutation.isSuccess && backgroundOrder && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
          <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-300">
            Búsqueda lanzada en segundo plano
          </h3>
          <p className="mt-1 text-sm text-blue-600 dark:text-blue-400">
            {backgroundOrder.query} se está procesando. Te avisaremos con el
            contador de nuevos resultados.
          </p>
          <Link
            href="/orders"
            className="mt-2 inline-block text-sm font-medium text-blue-700 underline hover:text-blue-800 dark:text-blue-300"
          >
            Ver el estado de mis búsquedas →
          </Link>
        </div>
      )}

      {backgroundMutation.isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
          <p className="text-sm text-red-700 dark:text-red-300">
            No se pudo lanzar la búsqueda en segundo plano. Inténtalo de nuevo.
          </p>
        </div>
      )}

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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} lines={4} />
          ))}
        </div>
      )}

      {/* Error State */}
      {searchMutation.isError && (() => {
        const copy = searchErrorMessage(searchMutation.error);
        return (
          <ErrorState
            title={copy.title}
            message={`${copy.detail}${copy.hint ? ` ${copy.hint}` : ""}`}
            onRetry={lastFilters ? handleRetry : undefined}
          />
        );
      })()}

      {/* Empty State */}
      {searchMutation.isSuccess && searchMutation.data.results.length === 0 && (
        <EmptyState
          title="No se encontraron vehículos"
          message="Prueba a ajustar los filtros de búsqueda (marca, modelo o rango de precio) para ver más resultados."
        />
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
