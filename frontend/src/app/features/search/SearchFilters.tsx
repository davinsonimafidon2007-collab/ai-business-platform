"use client";

import { useState } from "react";
import { Button } from "@/app/components/ui/button";
import type { SearchFilters as SearchFiltersType } from "@/app/types/vehicle";

interface SearchFiltersProps {
  onSearch: (filters: SearchFiltersType) => void;
  onBackgroundSearch?: (filters: SearchFiltersType) => void;
  isLoading?: boolean;
  initialQuery?: string;
}

const FUEL_TYPES = [
  { value: "", label: "Todos" },
  { value: "gasoline", label: "Gasolina" },
  { value: "diesel", label: "Diésel" },
  { value: "electric", label: "Eléctrico" },
  { value: "hybrid", label: "Híbrido" },
  { value: "plugin_hybrid", label: "Híbrido enchufable" },
];

const TRANSMISSIONS = [
  { value: "", label: "Todas" },
  { value: "manual", label: "Manual" },
  { value: "automatic", label: "Automática" },
  { value: "semi_automatic", label: "Semiautomática" },
];

const PROVIDERS = [
  { value: "", label: "Todos" },
  { value: "mobile_de", label: "Mobile.de" },
  { value: "autoscout24", label: "AutoScout24" },
];

const SORT_OPTIONS = [
  { value: "", label: "Relevancia" },
  { value: "price", label: "Precio" },
  { value: "year", label: "Año" },
  { value: "mileage", label: "Kilómetros" },
  { value: "score", label: "Puntuación" },
  { value: "roi", label: "ROI" },
  { value: "profit", label: "Beneficio" },
];

export function SearchFilters({ onSearch, onBackgroundSearch, isLoading, initialQuery }: SearchFiltersProps) {
  const [filters, setFilters] = useState<SearchFiltersType>({
    query: initialQuery || "",
    brand: "",
    model: "",
    min_price: undefined,
    max_price: undefined,
    min_mileage: undefined,
    max_mileage: undefined,
    fuel_type: "",
    transmission: "",
    min_year: undefined,
    max_year: undefined,
    provider: "",
    sort_by: "",
    sort_order: "desc",
    total_budget: undefined,
  });
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(filters);
  };

  const handleBackgroundSearch = () => {
    onBackgroundSearch?.(filters);
  };

  const handleReset = () => {
    setFilters({
      query: "",
      brand: "",
      model: "",
      min_price: undefined,
      max_price: undefined,
      min_mileage: undefined,
      max_mileage: undefined,
      fuel_type: "",
      transmission: "",
      min_year: undefined,
      max_year: undefined,
      provider: "",
      sort_by: "",
      sort_order: "desc",
      total_budget: undefined,
    });
  };

  const update = (key: keyof SearchFiltersType, value: string | number | undefined) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-secondary-200 bg-white p-4 dark:border-secondary-700 dark:bg-secondary-800" aria-label="Filtros de búsqueda de vehículos">
      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="flex-1">
          <label htmlFor="search-query" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">
            Búsqueda
          </label>
          <input
            id="search-query"
            type="text"
            value={filters.query}
            onChange={(e) => update("query", e.target.value)}
            placeholder="Ej: BMW Serie 3 2020..."
            aria-label="Buscar vehículos por marca, modelo o descripción"
            className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm text-secondary-900 placeholder-secondary-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100 dark:placeholder-secondary-500"
          />
        </div>
        <div className="w-full sm:w-44">
          <label
            htmlFor="total-budget"
            className="block text-sm font-medium text-secondary-700 dark:text-secondary-300"
          >
            Importe total (€)
          </label>
          <input
            id="total-budget"
            type="number"
            min={0}
            value={filters.total_budget ?? ""}
            onChange={(e) =>
              update("total_budget", e.target.value ? Number(e.target.value) : undefined)
            }
            placeholder="Ej: 12000"
            aria-label="Capital total disponible para la operación"
            className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm text-secondary-900 placeholder-secondary-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100 dark:placeholder-secondary-500"
          />
        </div>
        <div className="flex items-end gap-2">
          <Button type="submit" disabled={isLoading} aria-label="Buscar vehículos">
            {isLoading ? "Buscando..." : "Buscar"}
          </Button>
          {onBackgroundSearch && (
            <Button type="button" variant="outline" onClick={handleBackgroundSearch} aria-label="Buscar en segundo plano y notificar cuando hay resultados">
              Buscar en segundo plano
            </Button>
          )}
          <Button type="button" variant="ghost" onClick={handleReset} aria-label="Limpiar todos los filtros">
            Limpiar
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => setShowAdvanced(!showAdvanced)}
            aria-expanded={showAdvanced}
            aria-controls="advanced-filters"
          >
            {showAdvanced ? "Ocultar filtros" : "Más filtros"}
          </Button>
        </div>
      </div>

      {showAdvanced && (
        <div id="advanced-filters" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <div>
            <label htmlFor="filter-brand" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Marca</label>
            <input
              id="filter-brand"
              type="text"
              value={filters.brand || ""}
              onChange={(e) => update("brand", e.target.value)}
              placeholder="Ej: BMW"
              className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
            />
          </div>
          <div>
            <label htmlFor="filter-model" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Modelo</label>
            <input
              id="filter-model"
              type="text"
              value={filters.model || ""}
              onChange={(e) => update("model", e.target.value)}
              placeholder="Ej: 320d"
              className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
            />
          </div>
          <div>
            <label htmlFor="filter-min-price" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Precio mínimo</label>
            <input
              id="filter-min-price"
              type="number"
              value={filters.min_price || ""}
              onChange={(e) => update("min_price", e.target.value ? Number(e.target.value) : undefined)}
              placeholder="0"
              className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
            />
          </div>
          <div>
            <label htmlFor="filter-max-price" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Precio máximo</label>
            <input
              id="filter-max-price"
              type="number"
              value={filters.max_price || ""}
              onChange={(e) => update("max_price", e.target.value ? Number(e.target.value) : undefined)}
              placeholder="50000"
              className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
            />
          </div>
          <div>
            <label htmlFor="filter-min-mileage" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Km mínimos</label>
            <input
              id="filter-min-mileage"
              type="number"
              value={filters.min_mileage || ""}
              onChange={(e) => update("min_mileage", e.target.value ? Number(e.target.value) : undefined)}
              placeholder="0"
              className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
            />
          </div>
          <div>
            <label htmlFor="filter-max-mileage" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Km máximos</label>
            <input
              id="filter-max-mileage"
              type="number"
              value={filters.max_mileage || ""}
              onChange={(e) => update("max_mileage", e.target.value ? Number(e.target.value) : undefined)}
              placeholder="200000"
              className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
            />
          </div>
          <div>
            <label htmlFor="filter-fuel" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Combustible</label>
            <select
              id="filter-fuel"
              value={filters.fuel_type || ""}
              onChange={(e) => update("fuel_type", e.target.value)}
              className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
            >
              {FUEL_TYPES.map((ft) => (
                <option key={ft.value} value={ft.value}>{ft.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="filter-transmission" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Transmisión</label>
            <select
              id="filter-transmission"
              value={filters.transmission || ""}
              onChange={(e) => update("transmission", e.target.value)}
              className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
            >
              {TRANSMISSIONS.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="filter-min-year" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Año mínimo</label>
            <input
              id="filter-min-year"
              type="number"
              value={filters.min_year || ""}
              onChange={(e) => update("min_year", e.target.value ? Number(e.target.value) : undefined)}
              placeholder="2015"
              className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
            />
          </div>
          <div>
            <label htmlFor="filter-max-year" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Año máximo</label>
            <input
              id="filter-max-year"
              type="number"
              value={filters.max_year || ""}
              onChange={(e) => update("max_year", e.target.value ? Number(e.target.value) : undefined)}
              placeholder="2024"
              className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
            />
          </div>
          <div>
            <label htmlFor="filter-provider" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Proveedor</label>
            <select
              id="filter-provider"
              value={filters.provider || ""}
              onChange={(e) => update("provider", e.target.value)}
              className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="filter-sort" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Ordenar por</label>
            <select
              id="filter-sort"
              value={filters.sort_by || ""}
              onChange={(e) => update("sort_by", e.target.value)}
              className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
            >
              {SORT_OPTIONS.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="filter-order" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">Orden</label>
            <select
              id="filter-order"
              value={filters.sort_order || "desc"}
              onChange={(e) => update("sort_order", e.target.value as "asc" | "desc")}
              className="mt-1 block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2.5 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
            >
              <option value="desc">Descendente</option>
              <option value="asc">Ascendente</option>
            </select>
          </div>
        </div>
      )}
    </form>
  );
}