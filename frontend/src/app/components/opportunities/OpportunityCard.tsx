"use client";

import Link from "next/link";

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
    created_at?: string | null;
  };
}

export function OpportunityCard({ id, opportunity }: OpportunityCardProps) {
  const vehicle = opportunity.vehicle ?? {};
  const image = Array.isArray(vehicle.images) && vehicle.images[0] ? vehicle.images[0] : null;
  const title = [vehicle.brand, vehicle.model].filter(Boolean).join(" ") || "Vehículo";
  const year = vehicle.year ?? null;
  const price = vehicle.price ?? null;
  const profit = opportunity.estimated_profit ?? null;
  const roi = opportunity.roi_percentage ?? null;
  const recommendation = opportunity.recommendation_label_es ?? opportunity.recommendation ?? null;

  return (
    <Link
      href={`/opportunities/${id}`}
      className="flex flex-col sm:flex-row gap-4 p-4 rounded-2xl bg-[#111118] border border-[#1e1e2d] hover:border-[#2a2a3d] transition-all"
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
  );
}
