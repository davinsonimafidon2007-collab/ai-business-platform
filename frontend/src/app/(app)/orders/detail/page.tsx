"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { searchOrdersService } from "@/app/services/search-orders";
import { SkeletonCard } from "@/app/components/ui/Skeleton";
import { VehicleTable } from "@/app/features/vehicle/VehicleTable";
import { VehicleDrawer } from "@/app/features/vehicle/VehicleDrawer";
import type { SearchOrderDetail } from "@/app/types/search-orders";
import type { SearchResultItem } from "@/app/types/vehicle";

const STATUS_LABEL: Record<string, string> = {
  PENDING: "Pendiente",
  RUNNING: "En ejecución",
  COMPLETED: "Completada",
  FAILED: "Fallida",
};

const STATUS_STYLE: Record<string, string> = {
  PENDING: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  RUNNING: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
  COMPLETED: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  FAILED: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
};

function formatEur(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${new Intl.NumberFormat("es-ES").format(Math.round(value))} €`;
}

function OrderDetailContent({ id }: { id: string }) {
  const queryClient = useQueryClient();
  const [selectedVehicle, setSelectedVehicle] = useState<SearchResultItem | null>(
    null,
  );

  const { data: order, isLoading, error } = useQuery<SearchOrderDetail>({
    queryKey: ["search-order", id],
    queryFn: () => searchOrdersService.get(id),
    refetchInterval: 15000,
  });

  const markSeenMutation = useMutation({
    mutationFn: () => searchOrdersService.markSeen(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["search-order", id] });
      queryClient.invalidateQueries({ queryKey: ["search-orders"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-3 p-6">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="p-6">
        <p className="text-red-600">No se pudo cargar la búsqueda.</p>
        <Link
          href="/orders"
          className="mt-2 inline-block text-sm text-blue-600 hover:underline"
        >
          ← Volver a búsquedas
        </Link>
      </div>
    );
  }

  const vehicles: SearchResultItem[] = order.vehicles
    .filter((v) => v.result != null)
    .map((v) => v.result as SearchResultItem);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link
            href="/orders"
            className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Volver a búsquedas
          </Link>
          <h1 className="mt-2 text-xl font-bold text-secondary-900 dark:text-secondary-100 md:text-2xl">
            {order.query}
          </h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-secondary-500 dark:text-secondary-400">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[order.status]}`}
            >
              {STATUS_LABEL[order.status]}
            </span>
            <span>
              Presupuesto total: {formatEur(order.total_budget)} · Precio máx.
              compra: {formatEur(order.max_purchase_price)}
            </span>
            <span>{order.results_count} resultados</span>
          </div>
          {order.status === "FAILED" && order.error_message && (
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">
              Error: {order.error_message}
            </p>
          )}
        </div>
        {order.new_count > 0 && (
          <button
            onClick={() => markSeenMutation.mutate()}
            disabled={markSeenMutation.isPending}
            className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50"
          >
            Marcar todos como vistos
          </button>
        )}
      </div>

      {vehicles.length > 0 ? (
        <VehicleTable
          vehicles={vehicles}
          onSelectVehicle={setSelectedVehicle}
        />
      ) : (
        <div className="rounded-lg border border-dashed border-secondary-300 p-8 text-center text-secondary-500 dark:border-secondary-700">
          {order.status === "COMPLETED" || order.status === "FAILED"
            ? "No se encontraron vehículos para esta búsqueda."
            : "Esta búsqueda aún se está procesando en segundo plano. Actualiza en unos segundos."}
        </div>
      )}

      <VehicleDrawer
        vehicle={selectedVehicle}
        onClose={() => setSelectedVehicle(null)}
      />
    </div>
  );
}

function OrderDetailPageInner() {
  const params = useSearchParams();
  const id = params.get("id");

  if (!id) {
    return (
      <div className="p-6">
        <p className="text-red-600">Falta el identificador de la búsqueda.</p>
        <Link
          href="/orders"
          className="mt-2 inline-block text-sm text-blue-600 hover:underline"
        >
          ← Volver a búsquedas
        </Link>
      </div>
    );
  }

  return <OrderDetailContent id={id} />;
}

export default function OrderDetailPage() {
  return (
    <Suspense fallback={<div className="p-6">Cargando búsqueda...</div>}>
      <OrderDetailPageInner />
    </Suspense>
  );
}
