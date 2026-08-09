"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { dashboardService } from "@/app/services/dashboard";
import { StatCard } from "@/app/components/ui/StatCard";
import type {
  DashboardRecentOrder,
  DashboardStats,
  DashboardRecentVehicle,
  SearchOrderStatus,
} from "@/app/types/search-orders";

const STATUS_LABEL: Record<SearchOrderStatus, string> = {
  PENDING: "Pendiente",
  RUNNING: "En ejecución",
  COMPLETED: "Completada",
  FAILED: "Fallida",
};

const STATUS_STYLE: Record<SearchOrderStatus, string> = {
  PENDING: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  RUNNING: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
  COMPLETED: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  FAILED: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
};

function formatEur(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${new Intl.NumberFormat("es-ES").format(Math.round(value))} €`;
}

function OrderRow({ order }: { order: DashboardRecentOrder }) {
  return (
    <Link
      href={`/orders/${order.id}`}
      className="flex items-center justify-between rounded-lg border border-secondary-200 bg-white p-3 transition hover:border-secondary-300 dark:border-secondary-700 dark:bg-secondary-800"
    >
      <div className="min-w-0">
        <p className="truncate font-medium text-secondary-900 dark:text-secondary-100">
          {order.query}
        </p>
        <p className="text-xs text-secondary-500 dark:text-secondary-400">
          {order.results_count} resultados · {formatEur(order.max_purchase_price)}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {order.new_count > 0 && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
            {order.new_count} nuevos
          </span>
        )}
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[order.status]}`}
        >
          {STATUS_LABEL[order.status]}
        </span>
      </div>
    </Link>
  );
}

function VehicleCard({ vehicle }: { vehicle: DashboardRecentVehicle }) {
  const profitColor =
    vehicle.estimated_profit != null && vehicle.estimated_profit < 0
      ? "text-red-600 dark:text-red-400"
      : "text-green-600 dark:text-green-400";

  return (
    <div className="overflow-hidden rounded-lg border border-secondary-200 bg-white dark:border-secondary-700 dark:bg-secondary-800">
      {vehicle.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={vehicle.image_url}
          alt={`${vehicle.brand} ${vehicle.model}`}
          className="h-28 w-full object-cover"
        />
      ) : (
        <div className="flex h-28 items-center justify-center bg-secondary-100 text-secondary-400 dark:bg-secondary-700">
          Sin imagen
        </div>
      )}
      <div className="p-3">
        <p className="truncate font-medium text-secondary-900 dark:text-secondary-100">
          {vehicle.brand} {vehicle.model}
          {vehicle.year ? ` ${vehicle.year}` : ""}
        </p>
        <p className="text-sm text-secondary-500 dark:text-secondary-400">
          {formatEur(vehicle.price)}
        </p>
        <div className="mt-2 flex items-center justify-between">
          {vehicle.score != null ? (
            <span className="rounded-full bg-violet-100 px-2 py-0.5 text-xs font-semibold text-violet-800 dark:bg-violet-900/40 dark:text-violet-300">
              Score {vehicle.score}
            </span>
          ) : (
            <span className="text-xs text-secondary-400">Sin evaluar</span>
          )}
          <span className={`text-xs font-semibold ${profitColor}`}>
            {vehicle.has_evaluation ? `+${formatEur(vehicle.estimated_profit)}` : "—"}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: stats, isLoading, error } = useQuery<DashboardStats>({
    queryKey: ["dashboard", "stats"],
    queryFn: dashboardService.getStats,
    refetchInterval: 30000,
  });

  if (isLoading) {
    return <div className="p-6">Cargando panel...</div>;
  }

  if (error) {
    return <div className="p-6 text-red-600">Error al cargar el panel.</div>;
  }

  const newSearchResults = stats?.new_search_results ?? 0;

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            Panel
          </h1>
          <p className="text-secondary-500 dark:text-secondary-400">
            Tus vehículos, búsquedas e inspecciones
          </p>
        </div>
        <div className="flex items-center gap-2">
          {newSearchResults > 0 && (
            <Link
              href="/orders"
              className="inline-flex items-center gap-2 rounded-md bg-amber-100 px-3 py-2 text-sm font-semibold text-amber-800 transition hover:bg-amber-200 dark:bg-amber-900/40 dark:text-amber-300"
            >
              {newSearchResults} búsqueda{newSearchResults > 1 ? "s" : ""} con nuevos
              resultados
            </Link>
          )}
          <Link
            href="/search"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Nueva búsqueda
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          title="Vehículos"
          value={stats?.total_vehicles ?? 0}
          icon="🚗"
          subtitle={`${stats?.total_searches ?? 0} búsquedas realizadas`}
          trend="neutral"
        />
        <StatCard
          title="Nuevos resultados"
          value={newSearchResults}
          icon="🆕"
          subtitle={newSearchResults > 0 ? "en tus búsquedas" : "ninguno pendiente"}
          trend={newSearchResults > 0 ? "up" : "neutral"}
        />
        <StatCard
          title="Inspecciones"
          value={stats?.total_inspections ?? 0}
          icon="🔍"
          subtitle={`${stats?.completed_inspections ?? 0} completadas`}
          trend="neutral"
        />
        <StatCard
          title="Oportunidades"
          value={stats?.total_opportunities ?? 0}
          icon="💡"
          subtitle="vehículos con potencial"
          trend="neutral"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100">
              Búsquedas recientes
            </h2>
            <Link href="/orders" className="text-sm text-blue-600 hover:underline">
              Ver todas
            </Link>
          </div>
          {stats?.recent_orders?.length ? (
            <div className="space-y-2">
              {stats.recent_orders.map((order) => (
                <OrderRow key={order.id} order={order} />
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-secondary-300 p-6 text-center text-sm text-secondary-500 dark:border-secondary-700">
              Aún no tienes búsquedas. Lanza una desde{" "}
              <Link href="/search" className="text-blue-600 hover:underline">
                nueva búsqueda
              </Link>
              .
            </div>
          )}
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100">
              Últimos vehículos
            </h2>
            <Link href="/vehicles" className="text-sm text-blue-600 hover:underline">
              Ver todos
            </Link>
          </div>
          {stats?.recent_vehicles?.length ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {stats.recent_vehicles.map((vehicle) => (
                <VehicleCard key={vehicle.id} vehicle={vehicle} />
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-secondary-300 p-6 text-center text-sm text-secondary-500 dark:border-secondary-700">
              Todavía no has guardado vehículos.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
