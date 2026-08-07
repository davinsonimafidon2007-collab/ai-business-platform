"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { simulateProfit } from "@/app/services/simulateProfit";
import type { SimulateProfitResponse } from "@/app/services/simulateProfit";
import { updateDealSimulation } from "@/app/services/deals";
import { mapSimToDealUpdate } from "@/app/features/simulate/mapSimToDealUpdate";
import { RecommendationBadge } from "@/app/components/ui/ScoreBadge";
import { Button } from "@/app/components/ui/button";

const eur = (n?: number | null) =>
  n == null
    ? "—"
    : new Intl.NumberFormat("es-ES", {
        style: "currency",
        currency: "EUR",
        maximumFractionDigits: 0,
      }).format(n);

const pct = (n?: number | null) =>
  n == null ? "—" : `${Number(n).toFixed(2)} %`;

const PROFILES = ["SPAIN", "ES", "PORTUGAL", "PT"];

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

type CostKey =
  | "transport_cost"
  | "registration_cost"
  | "taxes"
  | "inspection_cost"
  | "commission_cost"
  | "repair_estimate"
  | "miscellaneous_cost";

const costRows: { key: CostKey; label: string }[] = [
  { key: "transport_cost", label: "Transporte" },
  { key: "registration_cost", label: "Matriculación" },
  { key: "taxes", label: "Impuestos" },
  { key: "inspection_cost", label: "Inspección" },
  { key: "commission_cost", label: "Comisión" },
  { key: "repair_estimate", label: "Reparaciones" },
  { key: "miscellaneous_cost", label: "Otros" },
];

function getErrorMessage(err: Error): string {
  const axiosErr = err as AxiosError;
  if (axiosErr.response) {
    const status = axiosErr.response.status;
    if (status === 422) {
      return "Indica un precio de compra (el vehículo no tiene precio definido).";
    }
    if (status === 401) {
      return "Sesión no autorizada. Inicia sesión de nuevo.";
    }
    if (status === 404) {
      return "Vehículo no encontrado o no pertenece a tu cuenta.";
    }
    const detail = axiosErr.response.data as
      | { detail?: string }
      | string
      | undefined;
    if (typeof detail === "object" && detail?.detail) {
      return detail.detail;
    }
  }
  return err.message || "Error al simular el margen.";
}

type Props = {
  vehicleId: string;
  defaultPurchasePrice?: number | null;
  dealId?: string | null;
  /** Si no hay dealId, permite crear el deal y luego guardar la simulación. Devuelve el deal id. */
  onEnsureDeal?: () => Promise<string>;
};

export function SimulateProfitPanel({
  vehicleId,
  defaultPurchasePrice,
  dealId,
  onEnsureDeal,
}: Props) {
  const [open, setOpen] = useState(false);
  const [purchasePrice, setPurchasePrice] = useState<string>(
    defaultPurchasePrice != null ? String(defaultPurchasePrice) : ""
  );
  const [salePrice, setSalePrice] = useState<string>("");
  const [profile, setProfile] = useState<string>("SPAIN");
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const simulate = useMutation({
    mutationFn: () =>
      simulateProfit(vehicleId, {
        profile_name: profile,
        purchase_price: purchasePrice ? Number(purchasePrice) : undefined,
        estimated_sale_price: salePrice ? Number(salePrice) : undefined,
      }),
  });

const saveSim = useMutation({
    mutationFn: () => {
      if (!dealId) throw new Error("No hay deal vinculado");
      if (!simulate.data) throw new Error("No hay simulación para guardar");
      return updateDealSimulation(dealId, mapSimToDealUpdate(simulate.data));
    },
    onSuccess: () => {
      setSavedMsg("Guardado en el deal");
      setSaveError(null);
    },
    onError: (err: Error) => {
      setSaveError(err.message || "Error al guardar en el deal");
      setSavedMsg(null);
    },
  });

  const saveWithDeal = useMutation({
    mutationFn: async () => {
      if (!simulate.data) throw new Error("No hay simulación para guardar");
      const id = dealId ?? (await onEnsureDeal?.());
      if (!id) throw new Error("No se pudo obtener el deal");
      return updateDealSimulation(id, mapSimToDealUpdate(simulate.data));
    },
    onSuccess: () => {
      setSavedMsg("Deal creado y simulación guardada");
      setSaveError(null);
    },
    onError: (err: Error) => {
      setSaveError(err.message || "Error al guardar en el deal");
      setSavedMsg(null);
    },
  });

  return (
    <div className="mt-4 border-t border-secondary-200 pt-4 dark:border-secondary-700">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "Cerrar simulación" : "Simular margen"}
      </Button>

      {open && (
        <div className="mt-4 rounded-lg border border-secondary-200 bg-secondary-50 p-4 dark:border-secondary-700 dark:bg-secondary-900/40">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-secondary-600 dark:text-secondary-300">
                Precio de compra (EUR)
              </label>
              <input
                type="number"
                min={0}
                step="0.01"
                value={purchasePrice}
                onChange={(e) => setPurchasePrice(e.target.value)}
                placeholder="ej. 18000"
                className="block w-40 rounded-md border border-secondary-300 bg-white px-3 py-1.5 text-sm text-secondary-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-secondary-600 dark:bg-secondary-900 dark:text-secondary-100"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-secondary-600 dark:text-secondary-300">
                Precio de venta estimado (EUR)
              </label>
              <input
                type="number"
                min={0}
                step="0.01"
                value={salePrice}
                onChange={(e) => setSalePrice(e.target.value)}
                placeholder="ej. 24000"
                className="block w-40 rounded-md border border-secondary-300 bg-white px-3 py-1.5 text-sm text-secondary-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-secondary-600 dark:bg-secondary-900 dark:text-secondary-100"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-secondary-600 dark:text-secondary-300">
                Perfil
              </label>
              <select
                value={profile}
                onChange={(e) => setProfile(e.target.value)}
                className="block rounded-md border border-secondary-300 bg-white px-3 py-1.5 text-sm text-secondary-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-secondary-600 dark:bg-secondary-900 dark:text-secondary-100"
              >
                {PROFILES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <Button
              variant="primary"
              size="sm"
              disabled={simulate.isPending}
              onClick={() => simulate.mutate()}
            >
              {simulate.isPending ? "Simulando..." : "Simular"}
            </Button>
          </div>

          {simulate.isError && (
            <p className="mt-3 text-sm text-red-600 dark:text-red-400">
              {getErrorMessage(simulate.error)}
            </p>
          )}

          {simulate.data && (
            <div className="mt-4 space-y-4">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                <div>
                  <p className="text-xs font-medium text-secondary-500 dark:text-secondary-400">
                    Beneficio neto
                  </p>
                  <p className="mt-1 text-xl font-bold text-secondary-900 dark:text-secondary-100">
                    {eur(simulate.data.net_profit)}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-secondary-500 dark:text-secondary-400">
                    ROI
                  </p>
                  <p className="mt-1 text-xl font-bold text-secondary-900 dark:text-secondary-100">
                    {pct(simulate.data.roi_percentage)}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-secondary-500 dark:text-secondary-400">
                    Coste total
                  </p>
                  <p className="mt-1 font-semibold text-secondary-900 dark:text-secondary-100">
                    {eur(simulate.data.total_cost)}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-secondary-500 dark:text-secondary-400">
                    Venta estimada
                  </p>
                  <p className="mt-1 font-semibold text-secondary-900 dark:text-secondary-100">
                    {eur(simulate.data.estimated_sale_price)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <RecommendationBadge
                    recommendation={
                      simulate.data.recommendation_label_es ||
                      simulate.data.recommendation
                    }
                  />
                  <span
                    className={`text-sm font-medium ${riskColor(
                      simulate.data.risk_level
                    )}`}
                  >
                    Riesgo: {simulate.data.risk_label_es || simulate.data.risk_level}
                  </span>
                </div>
              </div>

              {(simulate.data.coherence_warnings?.length ?? 0) > 0 && (
                <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-amber-700 dark:text-amber-400">
                  {simulate.data.coherence_warnings!.map((msg, i) => (
                    <li key={i}>{msg}</li>
                  ))}
                </ul>
              )}

              <div>
                <p className="mb-2 text-xs font-medium text-secondary-500 dark:text-secondary-400">
                  Desglose de costes
                </p>
                <div className="overflow-hidden rounded-lg border border-secondary-200 dark:border-secondary-700">
                  <table className="w-full text-left text-sm">
                    <tbody>
                      {(simulate.data.cost_lines?.length ?? 0) > 0
                        ? simulate.data.cost_lines!.map((line) => (
                            <tr
                              key={line.key}
                              className="odd:bg-white even:bg-secondary-50 dark:odd:bg-secondary-800 dark:even:bg-secondary-900/40"
                            >
                              <td className="px-3 py-2 text-secondary-600 dark:text-secondary-300">
                                {line.label_es}
                              </td>
                              <td className="px-3 py-2 text-right font-medium text-secondary-900 dark:text-secondary-100">
                                {eur(line.amount)}
                              </td>
                            </tr>
                          ))
                        : costRows.map((row) => (
                            <tr
                              key={row.key}
                              className="odd:bg-white even:bg-secondary-50 dark:odd:bg-secondary-800 dark:even:bg-secondary-900/40"
                            >
                              <td className="px-3 py-2 text-secondary-600 dark:text-secondary-300">
                                {row.label}
                              </td>
                              <td className="px-3 py-2 text-right font-medium text-secondary-900 dark:text-secondary-100">
                                {eur(simulate.data[row.key])}
                              </td>
                            </tr>
                          ))}
                    </tbody>
                  </table>
                </div>
              </div>

<div className="flex flex-wrap items-center gap-3">
                {dealId ? (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={saveSim.isPending}
                    onClick={() => saveSim.mutate()}
                  >
                    {saveSim.isPending ? "Guardando..." : "Guardar en deal"}
                  </Button>
                ) : (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={saveSim.isPending}
                    >
                      Guardar en deal
                    </Button>
                    <span className="text-xs text-secondary-500 dark:text-secondary-400">
                      Abre un deal para guardar la simulación
                    </span>
                    {onEnsureDeal && (
                      <Button
                        variant="primary"
                        size="sm"
                        disabled={saveWithDeal.isPending}
                        onClick={() => saveWithDeal.mutate()}
                      >
                        {saveWithDeal.isPending
                          ? "Creando..."
                          : "Crear deal y guardar"}
                      </Button>
                    )}
                  </>
                )}
                {savedMsg && (
                  <span className="text-sm font-medium text-green-600 dark:text-green-400">
                    {savedMsg}
                  </span>
                )}
                {saveError && (
                  <span className="text-sm font-medium text-red-600 dark:text-red-400">
                    {saveError}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
