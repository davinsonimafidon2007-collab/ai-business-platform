"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/app/services/api/client";
import { VehicleTable } from "@/app/features/vehicle/VehicleTable";
import { VehicleDrawer } from "@/app/features/vehicle/VehicleDrawer";
import type { Vehicle, SearchResultItem } from "@/app/types/vehicle";

async function fetchMyVehicles(): Promise<Vehicle[]> {
  const { data } = await api.get<Vehicle[]>("/vehicles");
  return data;
}

/**
 * Convierte un vehículo guardado (Vehicle, de GET /vehicles) al shape
 * que espera VehicleTable (SearchResultItem).
 *
 * Los vehículos guardados no tienen análisis (score, opportunity, etc.),
 * así que esos campos se rellenan como null.
 */
function toSearchResultItem(vehicle: Vehicle): SearchResultItem {
  return {
    source: vehicle.source,
    external_id: vehicle.external_id,
    url: vehicle.url,
    brand: vehicle.brand,
    model: vehicle.model,
    year: vehicle.year,
    mileage: vehicle.mileage,
    fuel_type: vehicle.fuel_type,
    transmission: vehicle.transmission,
    power_hp: vehicle.power_hp,
    price: vehicle.price,
    currency: vehicle.currency,
    location: vehicle.location,
    // El backend guarda images como JSON (array) desde la migración k3l4m5n6o7p8;
    // soportamos también el legacy string (CSV) por si quedó alguna fila antigua.
    images: (() => {
      const imgs = vehicle.images;
      if (Array.isArray(imgs)) return imgs.filter(Boolean);
      if (typeof imgs === "string") {
        return (imgs as string).split(",").map((s) => s.trim()).filter(Boolean);
      }
      return [];
    })(),
    description: vehicle.description,
    vehicle_score: null,
    market_estimation: null,
    profit_analysis: null,
    opportunity: null,
    negotiation: null,
  };
}

function TableRowSkeleton() {
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-secondary-200 bg-white p-6 dark:border-primary-900/40 dark:bg-secondary-900">
      <div className="flex items-center gap-4">
        <div className="h-12 w-16 animate-pulse rounded-lg bg-secondary-200 dark:bg-secondary-700" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-1/3 animate-pulse rounded bg-secondary-200 dark:bg-secondary-700" />
          <div className="h-3 w-1/4 animate-pulse rounded bg-secondary-200 dark:bg-secondary-700" />
        </div>
        <div className="h-8 w-24 animate-pulse rounded bg-secondary-200 dark:bg-secondary-700" />
      </div>
    </div>
  );
}

export default function VehiclesPage() {
  const { data: vehicles, isLoading, error } = useQuery({
    queryKey: ["vehicles"],
    queryFn: fetchMyVehicles,
  });
  const [selectedVehicle, setSelectedVehicle] = useState<SearchResultItem | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            Mis vehículos
          </h1>
          <p className="text-secondary-500 dark:text-secondary-400">
            Cargando tus vehículos guardados...
          </p>
        </div>
        <div className="space-y-4">
          <TableRowSkeleton />
          <TableRowSkeleton />
          <TableRowSkeleton />
        </div>
      </div>
    );
  }

  if (error) {
    return <div className="p-6 text-red-600">Error al cargar tus vehículos.</div>;
  }

  const items = (vehicles ?? []).map(toSearchResultItem);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
          Mis vehículos
        </h1>
        <p className="text-secondary-500 dark:text-secondary-400">
          Vehículos que has guardado desde búsquedas anteriores
        </p>
      </div>

      {items.length > 0 ? (
        <VehicleTable
          vehicles={items}
          onSelectVehicle={setSelectedVehicle}
        />
      ) : (
        <p className="text-secondary-500 dark:text-secondary-400">
          Todavía no tienes vehículos guardados. Guarda uno desde una búsqueda.
        </p>
      )}

      <VehicleDrawer
        vehicle={selectedVehicle}
        onClose={() => setSelectedVehicle(null)}
      />
    </div>
  );
}