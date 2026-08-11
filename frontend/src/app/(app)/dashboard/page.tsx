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

const RISK_STYLE: Record<string, string> = {
  ALTO: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  MEDIO: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  BAJO: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
};

function formatEur(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${new Intl.NumberFormat("es-ES").format(Math.round(value))} €`;
}

function OrderRow({ order }: { order: DashboardRecentOrder }) {
  return (
    <Link
      href={`/orders/detail/?id=${order.id}`}
      className="flex items-center gap-4 rounded-xl border border-secondary-100 bg-white p-4 transition-all hover:border-secondary-200 hover:shadow-sm dark:border-secondary-800 dark:bg-secondary-800/50 dark:hover:border-secondary-700"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-50 dark:bg-primary-900/20">
        <svg className="w-5 h-5 text-primary-600 dark:text-primary-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-secondary-900 dark:text-white">
          {order.query}
        </p>
        <p className="text-xs text-secondary-500 dark:text-secondary-400">
          {order.results_count} resultados · {formatEur(order.max_purchase_price)}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {order.new_count > 0 && (
          <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
            {order.new_count} nuevos
          </span>
        )}
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_STYLE[order.status]}`}
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
      ? "text-red-500"
      : "text-green-500";

  return (
    <div className="group overflow-hidden rounded-xl border border-secondary-100 bg-white transition-all hover:border-secondary-200 hover:shadow-md dark:border-secondary-800 dark:bg-secondary-800/50 dark:hover:border-secondary-700">
      {vehicle.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={vehicle.image_url}
          alt={`${vehicle.brand} ${vehicle.model}`}
          className="h-32 w-full object-cover transition-transform group-hover:scale-105"
        />
      ) : (
        <div className="flex h-32 items-center justify-center bg-secondary-50 text-secondary-300 dark:bg-secondary-700/50">
          <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
          </svg>
        </div>
      )}
      <div className="p-4">
        <p className="truncate font-semibold text-secondary-900 dark:text-white">
          {vehicle.brand} {vehicle.model}
          {vehicle.year ? ` ${vehicle.year}` : ""}
        </p>
        <p className="mt-1 text-sm font-medium text-secondary-600 dark:text-secondary-300">
          {formatEur(vehicle.price)}
        </p>
        <div className="mt-3 flex items-center justify-between">
          {vehicle.score != null ? (
            <span className="rounded-full bg-violet-100 px-2.5 py-1 text-xs font-bold text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
              Score {vehicle.score}
            </span>
          ) : (
            <span className="text-xs text-secondary-400">Sin evaluar</span>
          )}
          <span className={`text-sm font-bold ${profitColor}`}>
            {vehicle.has_evaluation ? `${vehicle.estimated_profit != null && vehicle.estimated_profit >= 0 ? "+" : ""}${formatEur(vehicle.estimated_profit)}` : "—"}
          </span>
        </div>
      </div>
    </div>
  );
}

function ActivityItem({ icon, text, time, color }: { icon: React.ReactNode; text: string; time: string; color: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${color}`}>
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-secondary-700 dark:text-secondary-300">{text}</p>
        <p className="text-xs text-secondary-400">{time}</p>
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
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
        Error al cargar el panel.
      </div>
    );
  }

  const newSearchResults = stats?.new_search_results ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900 dark:text-white">
            Dashboard
          </h1>
          <p className="text-secondary-500 dark:text-secondary-400">
            Automatiza. Supervisa. Decide.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {newSearchResults > 0 && (
            <Link
              href="/orders"
              className="inline-flex items-center gap-2 rounded-lg bg-amber-100 px-4 py-2.5 text-sm font-semibold text-amber-800 transition hover:bg-amber-200 dark:bg-amber-900/40 dark:text-amber-300"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
              </svg>
              {newSearchResults} búsqueda{newSearchResults > 1 ? "s" : ""} con nuevos resultados
            </Link>
          )}
          <Link
            href="/search"
            className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-primary-700 hover:shadow-md"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Nueva búsqueda
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-2 lg:grid-cols-4">
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

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-secondary-900 dark:text-white">
              Búsquedas recientes
            </h2>
            <Link href="/orders" className="text-sm font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400">
              Ver todas
            </Link>
          </div>
          {stats?.recent_orders?.length ? (
            <div className="space-y-3">
              {stats.recent_orders.map((order) => (
                <OrderRow key={order.id} order={order} />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-secondary-200 p-8 text-center dark:border-secondary-700">
              <svg className="mx-auto h-10 w-10 text-secondary-300 dark:text-secondary-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
              <p className="mt-3 text-sm text-secondary-500 dark:text-secondary-400">
                Aún no tienes búsquedas.{" "}
                <Link href="/search" className="font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400">
                  Lanza una
                </Link>
              </p>
            </div>
          )}
        </section>

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-secondary-900 dark:text-white">
              Actividad reciente
            </h2>
          </div>
          <div className="space-y-4 rounded-xl border border-secondary-100 bg-white p-4 dark:border-secondary-800 dark:bg-secondary-800/50">
            {stats?.recent_orders?.[0] && (
              <ActivityItem
                icon={<svg className="w-4 h-4 text-primary-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" /></svg>}
                text={`Búsqueda "${stats.recent_orders[0].query}" completada`}
                time="Hace 2 min"
                color="bg-primary-50 dark:bg-primary-900/20"
              />
            )}
            {stats?.recent_vehicles?.[0] && (
              <ActivityItem
                icon={<svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
                text={`${stats.recent_vehicles[0].brand} ${stats.recent_vehicles[0].model} evaluado`}
                time="Hace 10 min"
                color="bg-green-50 dark:bg-green-900/20"
              />
            )}
            <ActivityItem
              icon={<svg className="w-4 h-4 text-amber-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
              text="Análisis de mercado completado"
              time="Hace 30 min"
              color="bg-amber-50 dark:bg-amber-900/20"
            />
            <ActivityItem
              icon={<svg className="w-4 h-4 text-violet-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" /></svg>}
              text="Oportunidad detectada"
              time="Hace 1h"
              color="bg-violet-50 dark:bg-violet-900/20"
            />
          </div>
        </section>
      </div>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-secondary-900 dark:text-white">
            Últimos vehículos
          </h2>
          <Link href="/vehicles" className="text-sm font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400">
            Ver todos
          </Link>
        </div>
        {stats?.recent_vehicles?.length ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {stats.recent_vehicles.map((vehicle) => (
              <VehicleCard key={vehicle.id} vehicle={vehicle} />
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-secondary-200 p-8 text-center dark:border-secondary-700">
            <svg className="mx-auto h-10 w-10 text-secondary-300 dark:text-secondary-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12" />
            </svg>
            <p className="mt-3 text-sm text-secondary-500 dark:text-secondary-400">
              Todavía no has guardado vehículos.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
