"use client";

import { useState, useMemo } from "react";
import { VehicleRow } from "./VehicleRow";
import { Button } from "@/app/components/ui/button";
import { ScoreBadge, ProfitBadge, OpportunityBadge, RecommendationBadge } from "@/app/components/ui/ScoreBadge";
import type { SearchResultItem } from "@/app/types/vehicle";

interface VehicleTableProps {
  vehicles: SearchResultItem[];
  onSelectVehicle: (vehicle: SearchResultItem) => void;
  selectedVehicleId?: string;
}

type SortField = "price" | "year" | "mileage" | "score" | "roi" | "profit";

interface SortHeaderProps {
  field: SortField;
  children: React.ReactNode;
  sortField: SortField;
  sortOrder: "asc" | "desc";
  onSort: (field: SortField) => void;
}

function SortHeader({ field, children, sortField, sortOrder, onSort }: SortHeaderProps) {
  return (
    <th
      className="cursor-pointer whitespace-nowrap px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200"
      onClick={() => onSort(field)}
    >
      <div className="flex items-center gap-1">
        {children}
        {sortField === field && (
          <span>{sortOrder === "desc" ? "↓" : "↑"}</span>
        )}
      </div>
    </th>
  );
}

export function VehicleTable({ vehicles, onSelectVehicle, selectedVehicleId }: VehicleTableProps) {
  const [sortField, setSortField] = useState<SortField>("roi");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  const filtered = useMemo(() => {
    if (!searchTerm) return vehicles;
    const term = searchTerm.toLowerCase();
    return vehicles.filter(
      (v) =>
        v.brand?.toLowerCase().includes(term) ||
        v.model?.toLowerCase().includes(term) ||
        v.location?.toLowerCase().includes(term) ||
        v.source?.toLowerCase().includes(term)
    );
  }, [vehicles, searchTerm]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let aVal = 0;
      let bVal = 0;
      switch (sortField) {
        case "price":
          aVal = a.price || 0;
          bVal = b.price || 0;
          break;
        case "year":
          aVal = a.year || 0;
          bVal = b.year || 0;
          break;
        case "mileage":
          aVal = a.mileage || 0;
          bVal = b.mileage || 0;
          break;
        case "score":
          aVal = a.vehicle_score?.score || 0;
          bVal = b.vehicle_score?.score || 0;
          break;
        case "roi":
          aVal = a.opportunity?.roi || 0;
          bVal = b.opportunity?.roi || 0;
          break;
        case "profit":
          aVal = a.opportunity?.estimated_profit || 0;
          bVal = b.opportunity?.estimated_profit || 0;
          break;
      }
      return sortOrder === "desc" ? bVal - aVal : aVal - bVal;
    });
  }, [filtered, sortField, sortOrder]);

  const totalPages = Math.ceil(sorted.length / itemsPerPage);
  const paginated = sorted.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "desc" ? "asc" : "desc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  if (!vehicles || vehicles.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-secondary-500 dark:text-secondary-400">
          {vehicles.length} vehículos encontrados
        </p>
        <div className="relative">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Buscar en resultados..."
            className="block w-64 rounded-lg border border-secondary-300 bg-white px-3 py-2 pl-8 text-sm dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
          />
          <span className="pointer-events-none absolute left-2.5 top-2.5 text-secondary-400">🔍</span>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-secondary-200 dark:border-secondary-700">
        <table className="min-w-full divide-y divide-secondary-200 dark:divide-secondary-700">
          <thead className="bg-secondary-50 dark:bg-secondary-800">
            <tr>
              <th className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">
                Imagen
              </th>
              <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">
                Marca
              </th>
              <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">
                Modelo
              </th>
              <SortHeader field="year" sortField={sortField} sortOrder={sortOrder} onSort={handleSort}>Año</SortHeader>
              <SortHeader field="mileage" sortField={sortField} sortOrder={sortOrder} onSort={handleSort}>Km</SortHeader>
              <SortHeader field="price" sortField={sortField} sortOrder={sortOrder} onSort={handleSort}>Precio</SortHeader>
              <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">
                País
              </th>
              <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">
                Proveedor
              </th>
              <SortHeader field="score" sortField={sortField} sortOrder={sortOrder} onSort={handleSort}>Score</SortHeader>
              <SortHeader field="profit" sortField={sortField} sortOrder={sortOrder} onSort={handleSort}>Oportunidad</SortHeader>
              <SortHeader field="roi" sortField={sortField} sortOrder={sortOrder} onSort={handleSort}>ROI</SortHeader>
              <SortHeader field="profit" sortField={sortField} sortOrder={sortOrder} onSort={handleSort}>Beneficio</SortHeader>
              <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">
                Nivel
              </th>
              <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-secondary-500 dark:text-secondary-400">
                Recomendación
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-secondary-200 bg-white dark:divide-secondary-700 dark:bg-secondary-900">
            {paginated.map((vehicle, index) => (
              <VehicleRow
                key={`${vehicle.source}-${vehicle.external_id}-${index}`}
                vehicle={vehicle}
                onClick={() => onSelectVehicle(vehicle)}
                isSelected={selectedVehicleId === `${vehicle.source}-${vehicle.external_id}`}
              />
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
          >
            Anterior
          </Button>
          <span className="text-sm text-secondary-600 dark:text-secondary-400">
            Página {currentPage} de {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
          >
            Siguiente
          </Button>
        </div>
      )}
    </div>
  );
}