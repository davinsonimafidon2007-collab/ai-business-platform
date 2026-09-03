"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { convertOpportunityToDeal } from "@/app/services/opportunities";

interface OpportunityCardProps {
  id: string;
  opportunity: {
    vehicle?: {
      brand?: string | null;
      model?: string | null;
      year?: number | null;
      price?: number | null;
      images?: string[] | null;
      url?: string | null;
    } | null;
    score?: number | null;
    estimated_profit?: number | null;
    roi_percentage?: number | null;
    recommendation?: string | null;
    recommendation_label_es?: string | null;
    risk_level?: string | null;
    risk_label_es?: string | null;
    /** Confianza 0-100 de los datos (TASK 2): distinta de profit/roi y de risk. */
    confidence?: number | null;
    /** OPEN o CONVERTED (TASK 3): si ya se convirtió en un deal. */
    status?: string | null;
    created_at?: string | null;
  };
}

// Solo estas recomendaciones justifican crear un deal (ver
// OpportunityIntegrationService._CONVERTIBLE_RECOMMENDATIONS en el backend).
const CONVERTIBLE_RECOMMENDATIONS = new Set(["BUY_NOW", "NEGOTIATE"]);

export function OpportunityCard({ id, opportunity }: OpportunityCardProps) {
  const queryClient = useQueryClient();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const vehicle = opportunity.vehicle ?? {};
  const image = Array.isArray(vehicle.images) && vehicle.images[0] ? vehicle.images[0] : null;
  const title = [vehicle.brand, vehicle.model].filter(Boolean).join(" ") || "Vehículo";
  const year = vehicle.year ?? null;
  const price = vehicle.price ?? null;
  const profit = opportunity.estimated_profit ?? null;
  const roi = opportunity.roi_percentage ?? null;
  const recommendation = opportunity.recommendation_label_es ?? opportunity.recommendation ?? null;

  const isConverted = opportunity.status === "CONVERTED";
  const isConvertible =
    !isConverted &&
    !!opportunity.recommendation &&
    CONVERTIBLE_RECOMMENDATIONS.has(opportunity.recommendation);

  const convert = useMutation({
    mutationFn: () => convertOpportunityToDeal(id),
    onSuccess: () => {
      setErrorMsg(null);
      queryClient.invalidateQueries({ queryKey: ["opportunities"] });
      queryClient.invalidateQueries({ queryKey: ["deals"] });
    },
    onError: (err: Error) => {
      setErrorMsg(err.message || "No se pudo crear el deal");
    },
  });

  return (
    <div className="rounded-2xl bg-[#111118] border border-[#1e1e2d] hover:border-[#2a2a3d] transition-all">
      <Link
        href={`/opportunities/${id}`}
        className="flex flex-col sm:flex-row gap-4 p-4"
      >
        <div className="relative w-full sm:w-32 h-32 sm:h-24 rounded-xl overflow-hidden shrink-0 bg-[#16161f]">
          {image ? (
            <img
              src={image}
              alt={title}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-secondary-500">
              Sin imagen
            </div>
          )}
        </div>

        <div className="flex-1 flex flex-col justify-between">
          <div>
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-semibold text-white text-base leading-snug">{title}</h3>
              {recommendation ? (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 capitalize">
                  {recommendation}
                </span>
              ) : null}
            </div>
            <p className="text-xs text-secondary-400 mt-1">
              {year ?? "—"} {vehicle.url ? `· <a href="${vehicle.url}" target="_blank" rel="noreferrer" className="text-primary-400">Ver anuncio</a>` : ""}
            </p>
          </div>

          <div className="flex items-center justify-between gap-2 mt-3 pt-3 border-t border-[#1e1e2d]">
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-base font-bold text-white">
                  {price != null ? `${Number(price).toLocaleString("es-ES")} €` : "Precio no disponible"}
                </span>
              </div>
              <p className="text-[11px] text-emerald-400 font-medium">
                {profit != null && roi != null ? `+${Number(profit).toLocaleString("es-ES")} € · ROI ${Number(roi).toFixed(1)}%` : "Rentabilidad pendiente"}
              </p>
            </div>

            <div className="text-right">
              <span className="text-[11px] text-secondary-400 font-medium block">
                {opportunity.risk_label_es ?? opportunity.risk_level ?? "Riesgo no calculado"}
              </span>
              {opportunity.confidence != null ? (
                <span className="text-[10px] text-secondary-500 block mt-0.5">
                  Confianza {Math.round(opportunity.confidence)}%
                </span>
              ) : null}
            </div>
          </div>
        </div>
      </Link>

      {(isConvertible || isConverted) && (
        <div className="flex items-center justify-between gap-2 px-4 pb-4">
          {isConverted ? (
            <span className="text-[11px] font-medium text-secondary-500">
              Ya convertida en deal
            </span>
          ) : (
            <button
              type="button"
              disabled={convert.isPending}
              onClick={(e) => {
                e.preventDefault();
                convert.mutate();
              }}
              className="text-[11px] font-semibold px-3 py-1.5 rounded-lg bg-primary-600/10 text-primary-400 border border-primary-600/30 hover:bg-primary-600/20 disabled:opacity-50 transition-colors"
            >
              {convert.isPending ? "Creando deal..." : "Convertir en deal"}
            </button>
          )}
          {errorMsg && (
            <span className="text-[11px] text-red-400">{errorMsg}</span>
          )}
        </div>
      )}
    </div>
  );
}
