"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchOpportunities } from "@/app/services/opportunities";
import { createDeal, fetchDeals } from "@/app/services/deals";
import type { Opportunity } from "@/app/services/opportunities";
import { RecommendationBadge } from "@/app/components/ui/ScoreBadge";
import { Button } from "@/app/components/ui/button";
import { ErrorDisplay } from "@/app/components/ui/ErrorDisplay";
import { SimulateProfitPanel } from "@/app/features/simulate/SimulateProfitPanel";
import type { AxiosError } from "axios";

const eur = (n?: number | null) =>
  n == null
    ? "—"
    : new Intl.NumberFormat("es-ES", {
        style: "currency",
        currency: "EUR",
        maximumFractionDigits: 0,
      }).format(n);

const pct = (n?: number | null) =>
  n == null ? "—" : `${Number(n).toFixed(1)} %`;

const riskColor = (risk?: string | null) => {
  switch (risk) {
    case "LOW":
      return "text-green-600 dark:text-green-400";
    case "MEDIUM":
      return "text-yellow-600 dark:text-yellow-400";
    case "HIGH":
      return "text-red-600 dark:text-red-400";
    default:
      return "text-secondary-500 dark:text-secondary-400";
  }
};

function OpportunityRow({ opportunity }: { opportunity: Opportunity }) {
  const vehicle = opportunity.vehicle;
const title = vehicle
    ? [vehicle.brand, vehicle.model, vehicle.year]
        .filter(Boolean)
        .join(" ") || "Vehículo sin nombre"
    : "Vehículo sin datos";

const queryClient = useQueryClient();
  const [dealMsg, setDealMsg] = useState<string | null>(null);
  const [dealError, setDealError] = useState<string | null>(null);
  const [existingDealId, setExistingDealId] = useState<string | null>(null);

  // Detectar si ya hay un deal activo para esta oportunidad.
  const { data: dealData } = useQuery({
    queryKey: ["deals", "by-opportunity", opportunity.id],
    queryFn: () =>
      fetchDeals({ opportunity_id: opportunity.id }).then((r) => r.items),
    enabled: !!opportunity.id && !existingDealId,
  });
  const activeDealId =
    existingDealId ?? dealData?.find((d) => d.id)?.id ?? null;

  const openDeal = useMutation({
    mutationFn: () =>
      createDeal({
        opportunity_id: opportunity.id,
        vehicle_id: vehicle?.id,
      }),
onSuccess: (deal) => {
      setDealMsg("Deal creado");
      setDealError(null);
      setExistingDealId(deal.id);
      queryClient.invalidateQueries({ queryKey: ["deals"] });
      queryClient.invalidateQueries({
        queryKey: ["deals", "by-opportunity", opportunity.id],
      });
    },
    onError: (err: Error) => {
      const axiosErr = err as AxiosError;
      const status = axiosErr.response?.status;
      if (status === 409 || status === 422) {
        // Ya existe un deal activo para esta oportunidad.
        const detail = axiosErr.response?.data as
          | { message?: string; deal_id?: string }
          | string
          | undefined;
        const dealId =
          typeof detail === "object" && detail ? detail.deal_id : undefined;
        setExistingDealId(dealId ?? null);
        setDealError("Ya tienes un deal abierto para esta oportunidad");
        setDealMsg(null);
        return;
      }
      setDealError(err.message || "Error al crear el deal");
      setDealMsg(null);
    },
  });

  return (
    <div className="rounded-lg border border-secondary-200 bg-white p-4 dark:border-secondary-700 dark:bg-secondary-800">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="font-semibold text-secondary-900 dark:text-secondary-100">
            {title}
          </h3>
          <p className="mt-1 text-sm text-secondary-500 dark:text-secondary-400">
            {vehicle?.source || "Fuente desconocida"}
            {vehicle?.mileage != null && ` · ${vehicle.mileage.toLocaleString("es-ES")} km`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {opportunity.recommendation && (
            <RecommendationBadge recommendation={opportunity.recommendation} label={opportunity.recommendation_label_es} />
          )}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div>
          <p className="text-xs font-medium text-secondary-500 dark:text-secondary-400">
            Precio
          </p>
          <p className="mt-1 font-semibold text-secondary-900 dark:text-secondary-100">
            {eur(vehicle?.price)}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium text-secondary-500 dark:text-secondary-400">
            Score
          </p>
          <p className="mt-1 font-semibold text-secondary-900 dark:text-secondary-100">
            {opportunity.score != null ? Math.round(opportunity.score) : "—"}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium text-secondary-500 dark:text-secondary-400">
            Profit estimado
          </p>
          <p className="mt-1 font-semibold text-secondary-900 dark:text-secondary-100">
            {eur(opportunity.estimated_profit)}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium text-secondary-500 dark:text-secondary-400">
            ROI
          </p>
          <p className="mt-1 font-semibold text-secondary-900 dark:text-secondary-100">
            {pct(opportunity.roi_percentage)}
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm">
          <span className="text-secondary-500 dark:text-secondary-400">Riesgo: </span>
          <span className={`font-medium ${riskColor(opportunity.risk_level)}`}>
            {opportunity.risk_label_es || opportunity.risk_level || "—"}
          </span>
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {dealMsg && (
            <span className="text-sm font-medium text-green-600 dark:text-green-400">
              {dealMsg}
            </span>
          )}
{dealError && (
            <span className="text-sm font-medium text-red-600 dark:text-red-400">
              {dealError}
            </span>
          )}
          {existingDealId ? (
            <a
              href="/deals"
              className="inline-flex h-8 items-center rounded-lg bg-primary-600 px-3 text-sm font-medium text-white hover:bg-primary-700"
            >
              Ver deal
            </a>
          ) : (
            <Button
              variant="outline"
              size="sm"
              disabled={openDeal.isPending}
              onClick={() => openDeal.mutate()}
            >
              {openDeal.isPending ? "Creando..." : "Abrir deal"}
            </Button>
          )}
{vehicle?.url && (
            <a
              href={vehicle.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-8 items-center rounded-lg bg-primary-600 px-3 text-sm font-medium text-white hover:bg-primary-700"
            >
              Ver anuncio
            </a>
          )}
        </div>
      </div>

{vehicle?.id && (
        <SimulateProfitPanel
          vehicleId={vehicle.id}
          defaultPurchasePrice={vehicle.price}
          dealId={activeDealId}
          onEnsureDeal={async () => {
            if (activeDealId) return activeDealId;
            const deal = await createDeal({
              opportunity_id: opportunity.id,
              vehicle_id: vehicle?.id,
            });
            setExistingDealId(deal.id);
            queryClient.invalidateQueries({ queryKey: ["deals"] });
            return deal.id;
          }}
        />
      )}
    </div>
  );
}

function OpportunitiesContent() {
  const [recommendation, setRecommendation] = useState<string>("");
  const [minScore, setMinScore] = useState<string>("");

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["opportunities", recommendation, minScore],
    queryFn: () =>
      fetchOpportunities({
        recommendation: recommendation || undefined,
        min_score: minScore ? Number(minScore) : undefined,
      }),
  });

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            Oportunidades
          </h1>
          <p className="text-secondary-500 dark:text-secondary-400">
            Vehículos con potencial de importación detectados por el sistema
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          {isFetching ? "Actualizando..." : "Actualizar"}
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-secondary-200 bg-white p-4 dark:border-secondary-700 dark:bg-secondary-800">
        <div>
          <label
            htmlFor="recommendation-filter"
            className="mb-1 block text-xs font-medium text-secondary-500 dark:text-secondary-400"
          >
            Recomendación
          </label>
          <select
            id="recommendation-filter"
            value={recommendation}
            onChange={(e) => setRecommendation(e.target.value)}
            className="block rounded-md border border-secondary-300 bg-white px-3 py-1.5 text-sm text-secondary-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-secondary-600 dark:bg-secondary-900 dark:text-secondary-100"
          >
            <option value="">Todas</option>
            <option value="BUY_NOW">BUY_NOW</option>
            <option value="WATCH">WATCH</option>
            <option value="NEGOTIATE">NEGOTIATE</option>
            <option value="REJECT">REJECT</option>
          </select>
        </div>
        <div>
          <label
            htmlFor="min-score-filter"
            className="mb-1 block text-xs font-medium text-secondary-500 dark:text-secondary-400"
          >
            Score mínimo
          </label>
          <input
            id="min-score-filter"
            type="number"
            min={0}
            max={100}
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            placeholder="0-100"
            className="block w-28 rounded-md border border-secondary-300 bg-white px-3 py-1.5 text-sm text-secondary-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-secondary-600 dark:bg-secondary-900 dark:text-secondary-100"
          />
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="animate-pulse rounded-lg border border-secondary-200 p-4 dark:border-secondary-700"
            >
              <div className="h-4 w-48 rounded bg-secondary-200 dark:bg-secondary-700" />
              <div className="mt-2 h-3 w-32 rounded bg-secondary-200 dark:bg-secondary-700" />
              <div className="mt-4 grid grid-cols-4 gap-4">
                {[...Array(4)].map((_, j) => (
                  <div
                    key={j}
                    className="h-3 w-20 rounded bg-secondary-200 dark:bg-secondary-700"
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {isError && (
        <ErrorDisplay error={error} onRetry={() => refetch()} />
      )}

      {/* Empty */}
      {!isLoading && !isError && items.length === 0 && (
        <div className="rounded-lg border border-secondary-200 p-12 text-center dark:border-secondary-700">
          <p className="text-4xl">💼</p>
          <h3 className="mt-4 text-lg font-semibold text-secondary-900 dark:text-secondary-100">
            No hay oportunidades con estos filtros
          </h3>
          <p className="mt-2 text-sm text-secondary-500 dark:text-secondary-400">
            Prueba a cambiar los filtros o actualizar los datos.
          </p>
        </div>
      )}

      {/* Results */}
      {!isLoading && !isError && items.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-secondary-500 dark:text-secondary-400">
            {data?.total ?? items.length} oportunidad
            {(data?.total ?? items.length) !== 1 ? "es" : ""} encontrada
            {(data?.total ?? items.length) !== 1 ? "s" : ""}
          </p>
          {items.map((opp) => (
            <OpportunityRow key={opp.id} opportunity={opp} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function OpportunitiesPage() {
  return <OpportunitiesContent />;
}

