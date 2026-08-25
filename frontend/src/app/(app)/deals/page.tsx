"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchDeals, updateDealStatus } from "@/app/services/deals";
import type { Deal, DealStatus } from "@/app/services/deals";
import { offerPricePrefill } from "@/app/(app)/deals/offerPrefill";
import { Button } from "@/app/components/ui/button";
import { ErrorDisplay } from "@/app/components/ui/ErrorDisplay";

const eur = (n?: number | null) =>
  n == null
    ? "—"
    : new Intl.NumberFormat("es-ES", {
        style: "currency",
        currency: "EUR",
        maximumFractionDigits: 0,
      }).format(n);

const formatDate = (d?: string | null) =>
  d ? new Date(d).toLocaleDateString("es-ES") : "—";

const pct = (n?: number | null) =>
  n == null ? "—" : `${Number(n).toFixed(2)} %`;

const STATUS_LABELS: Record<DealStatus, string> = {
  NEW: "Nuevo",
  ANALYZING: "Analizando",
  NEGOTIATING: "Negociando",
  WON: "Ganado",
  LOST: "Perdido",
  CANCELLED: "Cancelado",
};

const STATUS_COLORS: Record<DealStatus, string> = {
  NEW: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  ANALYZING:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  NEGOTIATING:
    "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  WON: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  LOST: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  CANCELLED:
    "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
};

// Transiciones válidas (mismo mapa que el backend v2: DealService._TRANSITIONS).
// Estados que aceptan offer_price en la transición (fase de negociación/cierre).
const OFFER_PRICE_TARGETS: ReadonlySet<DealStatus> = new Set([
  "NEGOTIATING",
  "WON",
]);

const TRANSITIONS: Record<DealStatus, DealStatus[]> = {
  NEW: ["ANALYZING", "CANCELLED"],
  ANALYZING: ["NEGOTIATING", "LOST", "CANCELLED"],
  NEGOTIATING: ["WON", "LOST", "CANCELLED"],
  WON: [],
  LOST: [],
  CANCELLED: [],
};

const ALL_STATUSES: DealStatus[] = [
  "NEW",
  "ANALYZING",
  "NEGOTIATING",
  "WON",
  "LOST",
  "CANCELLED",
];

function StatusBadge({ status }: { status: DealStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

function DealRow({ deal }: { deal: Deal }) {
  const queryClient = useQueryClient();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [offerPriceInput, setOfferPriceInput] = useState<string>("");
  const [pendingTarget, setPendingTarget] = useState<DealStatus | null>(null);

  const transition = useMutation({
    mutationFn: (target: DealStatus) =>
      updateDealStatus(deal.id, {
        status: target,
        offer_price:
          OFFER_PRICE_TARGETS.has(target) && offerPriceInput
            ? Number(offerPriceInput)
            : undefined,
      }),
    onSuccess: () => {
      setErrorMsg(null);
      setPendingTarget(null);
      setOfferPriceInput("");
      queryClient.invalidateQueries({ queryKey: ["deals"] });
    },
    onError: (err: Error) => {
      setErrorMsg(err.message || "Error al cambiar el estado del deal");
    },
  });

  const nextActions = TRANSITIONS[deal.status] ?? [];

  const handleAction = (target: DealStatus) => {
    if (OFFER_PRICE_TARGETS.has(target)) {
      setOfferPriceInput(offerPricePrefill(deal));
      setPendingTarget(target);
      setErrorMsg(null);
      return;
    }
    transition.mutate(target);
  };

  return (
    <div className="rounded-lg border border-secondary-200 bg-white p-4 dark:border-secondary-700 dark:bg-secondary-800">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-secondary-900 dark:text-secondary-100">
              Deal {deal.id.slice(0, 8)}
            </h3>
            <StatusBadge status={deal.status} />
          </div>
          <p className="mt-1 text-sm text-secondary-500 dark:text-secondary-400">
            {deal.contact_channel
              ? `Canal: ${deal.contact_channel}`
              : "Sin canal de contacto"}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs font-medium text-secondary-500 dark:text-secondary-400">
            Oferta
          </p>
          <p className="mt-1 font-semibold text-secondary-900 dark:text-secondary-100">
            {eur(deal.offer_price)}
          </p>
        </div>
      </div>

      {deal.notes && (
        <p className="mt-3 rounded-md bg-secondary-50 p-3 text-sm text-secondary-600 dark:bg-secondary-900/40 dark:text-secondary-300">
          {deal.notes}
        </p>
      )}

      {deal.last_sim_net_profit != null && (
        <div className="mt-4 rounded-lg border border-secondary-200 bg-secondary-50 p-4 dark:border-secondary-700 dark:bg-secondary-900/40">
          <p className="text-xs font-medium text-secondary-500 dark:text-secondary-400">
            Última simulación
            {deal.last_sim_profile && ` · ${deal.last_sim_profile}`}
            {deal.last_sim_at && ` · ${formatDate(deal.last_sim_at)}`}
          </p>
          <div className="mt-2 flex flex-wrap gap-x-6 gap-y-2">
            <div>
              <p className="text-xs text-secondary-500 dark:text-secondary-400">
                Beneficio neto
              </p>
              <p className="font-semibold text-secondary-900 dark:text-secondary-100">
                {eur(deal.last_sim_net_profit)}
              </p>
            </div>
            <div>
              <p className="text-xs text-secondary-500 dark:text-secondary-400">
                ROI
              </p>
              <p className="font-semibold text-secondary-900 dark:text-secondary-100">
                {pct(deal.last_sim_roi)}
              </p>
            </div>
            <div>
              <p className="text-xs text-secondary-500 dark:text-secondary-400">
                Coste total
              </p>
              <p className="font-semibold text-secondary-900 dark:text-secondary-100">
                {eur(deal.last_sim_total_cost)}
              </p>
            </div>
            <div>
              <p className="text-xs text-secondary-500 dark:text-secondary-400">
                Compra
              </p>
              <p className="font-semibold text-secondary-900 dark:text-secondary-100">
                {eur(deal.last_sim_purchase_price)}
              </p>
            </div>
            <div>
              <p className="text-xs text-secondary-500 dark:text-secondary-400">
                Venta
              </p>
              <p className="font-semibold text-secondary-900 dark:text-secondary-100">
                {eur(deal.last_sim_sale_price)}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
<p className="text-xs text-secondary-500 dark:text-secondary-400">
          Creado: {formatDate(deal.created_at)} · Actualizado:{" "}
          {formatDate(deal.updated_at)}
        </p>

        {nextActions.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {nextActions.map((target) => (
              <Button
                key={target}
                variant={
                  target === "WON"
                    ? "primary"
                    : target === "LOST" || target === "CANCELLED"
                      ? "danger"
                      : "outline"
                }
                size="sm"
                disabled={transition.isPending}
                onClick={() => handleAction(target)}
              >
                {transition.isPending
                  ? "Actualizando..."
                  : `→ ${STATUS_LABELS[target]}`}
              </Button>
            ))}
          </div>
        ) : (
          <span className="text-xs font-medium text-secondary-400 dark:text-secondary-500">
            Deal terminal
          </span>
        )}
      </div>

      {pendingTarget != null && OFFER_PRICE_TARGETS.has(pendingTarget) && (
        <div className="mt-3 flex flex-wrap items-end gap-3 rounded-md bg-secondary-50 p-3 dark:bg-secondary-900/40">
          <div className="flex flex-col gap-1">
            <label
              htmlFor={`offer-price-${deal.id}`}
              className="text-xs font-medium text-secondary-600 dark:text-secondary-300"
            >
              Precio de oferta (EUR) — opcional
            </label>
            <input
              id={`offer-price-${deal.id}`}
              type="number"
              min={0}
              step="0.01"
              value={offerPriceInput}
              onChange={(e) => setOfferPriceInput(e.target.value)}
              placeholder="ej. 15000"
className="block w-40 rounded-md border border-secondary-300 bg-white px-3 py-1.5 text-sm text-secondary-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-secondary-600 dark:bg-secondary-900 dark:text-secondary-100"
            />
            {deal.last_sim_purchase_price != null && (
              <p className="text-xs text-secondary-500 dark:text-secondary-400">
                Prefill desde simulación (compra{" "}
                {eur(deal.last_sim_purchase_price)}
                {deal.last_sim_profile ? ` · ${deal.last_sim_profile}` : ""})
              </p>
            )}
          </div>
          <Button
            variant="primary"
            size="sm"
            disabled={transition.isPending}
            onClick={() => transition.mutate(pendingTarget)}
          >
            {transition.isPending
              ? "Guardando..."
              : `Confirmar → ${STATUS_LABELS[pendingTarget]}`}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={transition.isPending}
            onClick={() => {
              setPendingTarget(null);
              setOfferPriceInput("");
            }}
          >
            Cancelar
          </Button>
        </div>
      )}

      {errorMsg && (
        <p className="mt-3 text-sm text-red-600 dark:text-red-400">{errorMsg}</p>
      )}
    </div>
  );
}

function DealsContent() {
  const [status, setStatus] = useState<string>("");
  const [message, setMessage] = useState<string | null>(null);

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["deals", status],
    queryFn: () => fetchDeals({ status: (status as DealStatus) || undefined }),
  });

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            Deals
          </h1>
          <p className="text-secondary-500 dark:text-secondary-400">
            Pipeline de gestión de tus tratos
          </p>
        </div>
        <div className="flex items-center gap-2">
          {message && (
            <span className="text-sm text-green-600 dark:text-green-400">
              {message}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            {isFetching ? "Actualizando..." : "Actualizar"}
          </Button>
        </div>
      </div>

      {/* Filter */}
      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-secondary-200 bg-white p-4 dark:border-secondary-700 dark:bg-secondary-800">
        <div>
          <label
            htmlFor="status-filter"
            className="mb-1 block text-xs font-medium text-secondary-500 dark:text-secondary-400"
          >
            Estado
          </label>
          <select
            id="status-filter"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="block rounded-md border border-secondary-300 bg-white px-3 py-1.5 text-sm text-secondary-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-secondary-600 dark:bg-secondary-900 dark:text-secondary-100"
          >
            <option value="">Todos</option>
            {ALL_STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
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
              <div className="mt-4 h-8 w-48 rounded bg-secondary-200 dark:bg-secondary-700" />
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
          <p className="text-4xl">🤝</p>
          <h3 className="mt-4 text-lg font-semibold text-secondary-900 dark:text-secondary-100">
            No hay deals con estos filtros
          </h3>
          <p className="mt-2 text-sm text-secondary-500 dark:text-secondary-400">
            Crea un deal desde una oportunidad para empezar.
          </p>
        </div>
      )}

      {/* Results */}
      {!isLoading && !isError && items.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-secondary-500 dark:text-secondary-400">
            {data?.total ?? items.length} deal
            {(data?.total ?? items.length) !== 1 ? "s" : ""} encontrado
            {(data?.total ?? items.length) !== 1 ? "s" : ""}
          </p>
          {items.map((deal) => (
            <DealRow key={deal.id} deal={deal} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DealsPage() {
  return <DealsContent />;
}
