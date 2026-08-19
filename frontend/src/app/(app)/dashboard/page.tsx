"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useSearchHistory, useDashboardStats } from "@/app/hooks/use-search";
import {
  fetchOpportunities,
  type Opportunity,
} from "@/app/services/opportunities";
import { fetchHealth } from "@/app/services/health";
import { useNetworkStatus } from "@/app/hooks/useNetworkStatus";
import { useAuthStore } from "@/app/store/auth-store";
import { HomeGreeting } from "@/app/features/home/HomeGreeting";
import { KpiRow } from "@/app/features/home/KpiRow";
import { HomeSection } from "@/app/features/home/HomeSection";
import {
  OpportunityTeaserCard,
  type BadgeTone,
} from "@/app/features/home/OpportunityTeaserCard";
import { RecentItemCard } from "@/app/features/home/RecentItemCard";
import { ErrorDisplay } from "@/app/components/ui/ErrorDisplay";

const eur = (n?: number | null) =>
  n == null
    ? "—"
    : new Intl.NumberFormat("es-ES", {
        style: "currency",
        currency: "EUR",
        maximumFractionDigits: 0,
      }).format(n);

const vehicleTitle = (opp: Opportunity): string => {
  const v = opp.vehicle;
  if (!v) return "Vehículo sin datos";
  return [v.brand, v.model, v.year].filter(Boolean).join(" ") || "Vehículo sin nombre";
};

const recommendationTone = (recommendation?: string | null): BadgeTone => {
  switch (recommendation) {
    case "BUY_NOW":
    case "BUY":
      return "success";
    case "WATCH":
    case "CONSIDER":
      return "info";
    case "NEGOTIATE":
      return "warning";
    case "REJECT":
      return "danger";
    default:
      return "neutral";
  }
};

function RowSkeleton() {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-secondary-200 bg-white p-4 dark:border-primary-900/40 dark:bg-secondary-900">
      <div className="h-10 w-10 flex-none animate-pulse rounded-xl bg-secondary-200 dark:bg-secondary-700" />
      <div className="flex-1 space-y-2">
        <div className="h-3 w-2/3 animate-pulse rounded bg-secondary-200 dark:bg-secondary-700" />
        <div className="h-2.5 w-1/3 animate-pulse rounded bg-secondary-200 dark:bg-secondary-700" />
      </div>
    </div>
  );
}

function EmptyOpportunities() {
  return (
    <div className="rounded-2xl border border-secondary-200 bg-white p-8 text-center dark:border-primary-900/40 dark:bg-secondary-900">
      <p className="text-3xl">🔍</p>
      <h3 className="mt-3 text-sm font-semibold text-secondary-900 dark:text-secondary-100">
        Aún no hay oportunidades
      </h3>
      <p className="mt-1 text-xs text-secondary-500 dark:text-secondary-400">
        Busca un vehículo para descubrir márgenes y oportunidades.
      </p>
      <Link
        href="/search"
        className="mt-3 inline-flex rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700"
      >
        Buscar un vehículo
      </Link>
    </div>
  );
}

function EmptyActivity() {
  return (
    <div className="rounded-2xl border border-secondary-200 bg-white p-8 text-center dark:border-primary-900/40 dark:bg-secondary-900">
      <p className="text-3xl">📋</p>
      <h3 className="mt-3 text-sm font-semibold text-secondary-900 dark:text-secondary-100">
        Sin actividad aún
      </h3>
      <p className="mt-1 text-xs text-secondary-500 dark:text-secondary-400">
        Realiza tu primera búsqueda para empezar.
      </p>
      <Link
        href="/search"
        className="mt-3 inline-flex rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700"
      >
        Ir a buscar
      </Link>
    </div>
  );
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const networkStatus = useNetworkStatus();
  const isOffline = !networkStatus.isOnline;
  const { data: history, isLoading: historyLoading, isError: historyError, refetch: refetchHistory } = useSearchHistory();
  const { data: stats, isLoading: statsLoading, isError: statsError, refetch: refetchStats } = useDashboardStats();
  const { data: opportunities, isLoading: oppLoading, isError: oppError, refetch: refetchOpps } = useQuery({
    queryKey: ["opportunities", "home"],
    queryFn: () => fetchOpportunities({ limit: 5 }),
  });
  const { data: health, isError: healthError } = useQuery({
    queryKey: ["health", "dashboard"],
    queryFn: fetchHealth,
    retry: 1,
    staleTime: 30_000,
  });

  const backendDown = healthError && !health;
  const anyError = historyError || statsError || oppError;
  const refetchAll = () => {
    void refetchHistory();
    void refetchStats();
    void refetchOpps();
  };

  const totalSearches = stats?.total_searches ?? history?.length ?? 0;
  const totalVehicles =
    history?.reduce((sum, h) => sum + (h.results_count || 0), 0) || 0;
  const averageResultsPerSearch =
    stats?.average_results_per_search ??
    (totalSearches > 0 ? Math.round(totalVehicles / totalSearches) : 0);
  const oppItems = opportunities?.items ?? [];
  const oppTotal = opportunities?.total ?? oppItems.length;
  const estProfit = oppItems.reduce(
    (sum, o) => sum + (o.estimated_profit || 0),
    0
  );

  const kpis = [
    {
      label: "Búsquedas",
      value: totalSearches,
      hint: totalSearches > 0 ? "Total acumulado" : "Sin actividad aún",
    },
    {
      label: "Vehículos en el radar",
      value: totalVehicles,
      hint:
        totalVehicles > 0 ? `${averageResultsPerSearch} por búsqueda` : "Sin datos",
    },
    { label: "Oportunidades", value: oppTotal, hint: "Destacadas" },
    {
      label: "Beneficio est.",
      value: estProfit > 0 ? eur(estProfit) : "—",
      hint: oppItems.length > 0 ? "Σ oportunidades" : "Sin estimaciones",
    },
  ];

  return (
    <div className="space-y-5">
      <HomeGreeting name={user?.full_name ?? user?.email} />

      <KpiRow items={kpis} />

      {/* CTA principal */}
      <Link
        href="/search"
        className="mt-4 flex items-center justify-center gap-2 rounded-2xl bg-primary-600 px-4 py-3 text-center text-sm font-semibold text-white shadow-sm shadow-primary-900/20 transition-colors hover:bg-primary-700"
      >
        <Search className="h-4 w-4" aria-hidden />
        Buscar vehículos
      </Link>

      {isOffline && (
        <div className="rounded-2xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/20">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Sin conexión a internet. Los datos mostrados pueden estar desactualizados.
          </p>
        </div>
      )}

      {backendDown && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-900/20">
          <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
            No se pudo conectar con el backend. Algunos datos pueden no estar disponibles.
          </p>
          <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
            Si estás en un dispositivo físico, ve a{" "}
            <Link href="/settings" className="font-medium underline">Configuración</Link>{" "}
            para configurar la URL del servidor.
          </p>
        </div>
      )}

      {anyError && (
        <ErrorDisplay
          error={new Error("No se pudieron cargar los datos del dashboard")}
          onRetry={refetchAll}
        />
      )}

      {/* Oportunidades + Actividad (stack en móvil, grid 2 cols en desktop) */}
      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <HomeSection title="Oportunidades destacadas" href="/opportunities">
          {oppLoading ? (
            <div className="space-y-3">
              <RowSkeleton />
              <RowSkeleton />
              <RowSkeleton />
            </div>
          ) : oppError ? (
            <ErrorDisplay
              error={new Error("Error al cargar oportunidades")}
              onRetry={refetchOpps}
            />
          ) : oppItems.length === 0 ? (
            <EmptyOpportunities />
          ) : (
            <div className="space-y-3">
              {oppItems.slice(0, 5).map((opp) => (
                <OpportunityTeaserCard
                  key={opp.id}
                  href="/opportunities"
                  title={vehicleTitle(opp)}
                  subtitle={
                    opp.recommendation_label_es ||
                    opp.recommendation ||
                    opp.vehicle?.source ||
                    "Sin recomendación"
                  }
                  badge={{
                    label:
                      opp.score != null ? `${Math.round(opp.score)} pts` : "—",
                    tone: recommendationTone(opp.recommendation),
                  }}
                  meta={
                    opp.estimated_profit != null
                      ? eur(opp.estimated_profit)
                      : undefined
                  }
                />
              ))}
            </div>
          )}
        </HomeSection>

        <HomeSection title="Actividad reciente" href="/history">
          {historyLoading ? (
            <div className="space-y-3">
              <RowSkeleton />
              <RowSkeleton />
              <RowSkeleton />
            </div>
          ) : historyError ? (
            <ErrorDisplay
              error={new Error("Error al cargar el historial")}
              onRetry={refetchHistory}
            />
          ) : !history || history.length === 0 ? (
            <EmptyActivity />
          ) : (
            <div className="space-y-3">
              {history.slice(0, 5).map((s) => (
                <RecentItemCard
                  key={s.id}
                  href="/history"
                  title={s.query || "Búsqueda"}
                  subtitle={
                    s.timestamp
                      ? new Date(s.timestamp).toLocaleDateString("es-ES", {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      : undefined
                  }
                  meta={
                    (s.results_count ?? 0) > 0
                      ? `${s.results_count} resultados`
                      : undefined
                  }
                />
              ))}
            </div>
          )}
        </HomeSection>
      </div>
    </div>
  );
}
