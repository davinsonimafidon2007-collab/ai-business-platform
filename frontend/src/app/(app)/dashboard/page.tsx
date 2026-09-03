"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Search, Plus, Briefcase, Loader2, Clock, CheckCircle2 } from "lucide-react";
import { useSearchHistory } from "@/app/hooks/use-search";
import { useApprovals } from "@/app/hooks/useApprovals";
import {
  fetchOpportunities,
  type Opportunity,
} from "@/app/services/opportunities";
import { fetchPortfolioSummary } from "@/app/services/deals";
import { fetchHealth } from "@/app/services/health";
import { useNetworkStatus } from "@/app/hooks/useNetworkStatus";
import { useAuthStore } from "@/app/store/auth-store";
import { HomeGreeting } from "@/app/features/home/HomeGreeting";
import { KpiRow } from "@/app/features/home/KpiRow";
import { HomeSection } from "@/app/features/home/HomeSection";
import { PhaseFlowStepper, type PhaseFlowStep } from "@/app/features/home/PhaseFlowStepper";
import { ApprovalTaskCard, timeAgoEs } from "@/app/features/home/ApprovalTaskCard";
import {
  OpportunityTeaserCard,
  type BadgeTone,
} from "@/app/features/home/OpportunityTeaserCard";
import { RecentItemCard } from "@/app/features/home/RecentItemCard";
import { SkeletonCard, ErrorState, EmptyState } from "@/components/ui/StateComponents";

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

export default function DashboardPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const { isOnline } = useNetworkStatus();
  const isOffline = !isOnline;

  const { data: history, isLoading: historyLoading, isError: historyError, refetch: refetchHistory } = useSearchHistory();
  const { data: opportunities, isLoading: oppLoading, isError: oppError, refetch: refetchOpps } = useQuery({
    queryKey: ["opportunities", "home"],
    queryFn: () => fetchOpportunities({ limit: 5 }),
  });
  const { data: openOpps } = useQuery({
    queryKey: ["opportunities", "open-count"],
    queryFn: () => fetchOpportunities({ status: "OPEN", limit: 1 }),
  });
  const { data: portfolio, isLoading: portfolioLoading } = useQuery({
    queryKey: ["deals-portfolio-summary", "dashboard"],
    queryFn: fetchPortfolioSummary,
  });
  const { data: approvals, isLoading: approvalsLoading } = useApprovals();
  const { data: health, isError: healthError } = useQuery({
    queryKey: ["health", "dashboard"],
    queryFn: fetchHealth,
    retry: 1,
    staleTime: 30_000,
  });

  const backendDown = healthError && !health;
  const anyError = historyError || oppError;
  const refetchAll = () => {
    void refetchHistory();
    void refetchOpps();
  };

  const oppItems = opportunities?.items ?? [];
  const byStatus = portfolio?.by_status ?? {};

  // KPIs: conteos reales (oportunidades abiertas, deals activos/vendidos,
  // aprobaciones pendientes reales) — no hay ningún número inventado.
  const activeOpportunities = openOpps?.total ?? 0;
  const inProgress = portfolio?.pipeline_count ?? 0;
  const pendingApproval = approvals?.length ?? 0;
  const completed = portfolio?.sold_count ?? 0;
  const kpiSum = inProgress + pendingApproval + completed;
  const pct = (n: number) => (kpiSum > 0 ? `${Math.round((n / kpiSum) * 100)}% del total` : undefined);

  const kpis = [
    {
      label: "Oportunidades",
      value: activeOpportunities,
      hint: "Activas",
      icon: Briefcase,
      tone: "info" as const,
    },
    {
      label: "En progreso",
      value: inProgress,
      hint: pct(inProgress),
      icon: Loader2,
      tone: "primary" as const,
    },
    {
      label: "Pendientes",
      value: pendingApproval,
      hint: pct(pendingApproval),
      icon: Clock,
      tone: "warning" as const,
    },
    {
      label: "Completadas",
      value: completed,
      hint: pct(completed),
      icon: CheckCircle2,
      tone: "success" as const,
    },
  ];

  // Flujo de fases: agrupación de los mismos estados reales de deals
  // (GET /deals/reports/portfolio) en 5 etapas de negocio. No es un
  // conteo nuevo/inventado, solo otra forma de mostrar by_status.
  const phaseFlow: PhaseFlowStep[] = [
    {
      key: "busqueda",
      label: "Búsqueda",
      count: (byStatus.NEW ?? 0) + (byStatus.ANALYZING ?? 0),
    },
    {
      key: "documentacion",
      label: "Documentación",
      count: (byStatus.NEGOTIATING ?? 0) + (byStatus.WON ?? 0),
    },
    {
      key: "traslado",
      label: "Traslado",
      count: (byStatus.BOUGHT ?? 0) + (byStatus.IN_TRANSIT ?? 0),
    },
    {
      key: "matriculacion",
      label: "Matriculación",
      count: byStatus.REGISTERED ?? 0,
    },
    { key: "venta", label: "Venta", count: byStatus.SOLD ?? 0 },
  ];
  const hasAnyDeals = phaseFlow.some((s) => s.count > 0);

  const pendingApprovals = (approvals ?? []).slice(0, 2);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <HomeGreeting name={user?.full_name ?? user?.email} />
        <Link
          href="/search/"
          className="flex items-center gap-1.5 rounded-xl bg-primary-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm shadow-primary-900/20 transition-colors hover:bg-primary-700"
        >
          <Plus className="h-4 w-4" aria-hidden />
          Nueva oportunidad
        </Link>
      </div>

      <KpiRow items={kpis} />

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
        <ErrorState
          title="Error al cargar dashboard"
          message="No se pudieron cargar los datos del dashboard. Verifica la conexión con el servidor."
          onRetry={refetchAll}
        />
      )}

      {/* Flujo de fases: solo se muestra si hay algún deal activo o cerrado */}
      {!portfolioLoading && hasAnyDeals && (
        <HomeSection title="Flujo de fases" href="/deals/">
          <div className="rounded-2xl border border-secondary-200 bg-white p-3 dark:border-secondary-700 dark:bg-secondary-900">
            <PhaseFlowStepper steps={phaseFlow} />
          </div>
        </HomeSection>
      )}

      {/* Tareas que requieren aprobación */}
      {!approvalsLoading && pendingApprovals.length > 0 && (
        <HomeSection
          title={`Tareas que requieren tu aprobación (${approvals?.length ?? 0})`}
          href="/approvals/"
        >
          <div className="space-y-2">
            {pendingApprovals.map((task) => (
              <ApprovalTaskCard
                key={task.id}
                title={task.title}
                category={task.category}
                description={task.description}
                timeLabel={timeAgoEs(task.created_at)}
              />
            ))}
          </div>
        </HomeSection>
      )}

      {/* Oportunidades + Actividad (stack en móvil, grid 2 cols en desktop) */}
      <div className="grid gap-6 md:grid-cols-2">
        <HomeSection title="Oportunidades destacadas" href="/opportunities">
          {oppLoading ? (
            <div className="space-y-3">
              <SkeletonCard lines={2} />
              <SkeletonCard lines={2} />
            </div>
          ) : oppError ? (
            <ErrorState
              title="Error al cargar oportunidades"
              message="No se pudieron cargar las oportunidades destacadas."
              onRetry={refetchOpps}
            />
          ) : oppItems.length === 0 ? (
            <EmptyState
              title="Aún no hay oportunidades"
              message="Busca un vehículo para descubrir márgenes y oportunidades."
              action={{
                label: "Buscar un vehículo",
                onClick: () => {
                  router.push("/search");
                },
              }}
            />
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
              <SkeletonCard lines={2} />
              <SkeletonCard lines={2} />
            </div>
          ) : historyError ? (
            <ErrorState
              title="Error al cargar historial"
              message="No se pudo obtener el historial de búsqueda."
              onRetry={refetchHistory}
            />
          ) : !history || history.length === 0 ? (
            <EmptyState
              title="Sin actividad aún"
              message="Realiza tu primera búsqueda para empezar."
              action={{
                label: "Ir a buscar",
                onClick: () => {
                  router.push("/search");
                },
              }}
            />
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

      {/* CTA secundaria (móvil: acceso directo a búsqueda) */}
      <Link
        href="/search"
        className="flex items-center justify-center gap-2 rounded-2xl border border-primary-600/40 bg-primary-600/10 px-4 py-3 text-center text-sm font-semibold text-primary-600 transition-colors hover:bg-primary-600/20 dark:text-primary-400 sm:hidden"
      >
        <Search className="h-4 w-4" aria-hidden />
        Buscar vehículos
      </Link>
    </div>
  );
}
