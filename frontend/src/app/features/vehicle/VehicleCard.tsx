"use client";

import { cn } from "@/app/utils/cn";
import { ScoreBadge, ProfitBadge, OpportunityBadge, RecommendationBadge, NegotiationBadge } from "@/app/components/ui/ScoreBadge";
import type { SearchResultItem } from "@/app/types/vehicle";

interface VehicleCardProps {
  vehicle: SearchResultItem;
  onClick: () => void;
}

export function VehicleCard({ vehicle, onClick }: VehicleCardProps) {
  const opp = vehicle.opportunity;
  const score = vehicle.vehicle_score;

  return (
    <button
      onClick={onClick}
      className="flex w-full flex-col overflow-hidden rounded-xl border border-secondary-200 bg-white text-left transition-colors active:bg-secondary-50 dark:border-secondary-700 dark:bg-secondary-800 dark:active:bg-secondary-700"
    >
      <div className="relative h-40 w-full bg-secondary-100 dark:bg-secondary-700">
        {vehicle.images && vehicle.images[0] ? (
          <img
            src={vehicle.images[0]}
            alt={`${vehicle.brand} ${vehicle.model}`}
            className="h-full w-full object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'%3E%3Crect width='160' height='160' fill='%23e5e7eb'/%3E%3Ctext x='80' y='80' text-anchor='middle' dy='.3em' fill='%239ca3af' font-size='14'%3ESin imagen%3C/text%3E%3C/svg%3E";
            }}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-secondary-100 text-xs text-secondary-400 dark:bg-secondary-700">
            <svg className="h-10 w-10 text-secondary-300 dark:text-secondary-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12" />
            </svg>
          </div>
        )}
        <div className="absolute left-2 top-2 flex gap-1.5">
          {score && <ScoreBadge score={score.score} />}
          {opp && <OpportunityBadge level={opp.opportunity_level} />}
        </div>
        {opp && (
          <div className="absolute bottom-2 right-2 rounded-lg bg-white/90 px-2 py-1 shadow-sm backdrop-blur dark:bg-secondary-900/90">
            <ProfitBadge value={opp.estimated_profit} />
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 p-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-secondary-900 dark:text-secondary-100">
              {vehicle.brand || "-"} {vehicle.model || ""}
            </p>
            <p className="mt-0.5 text-xs text-secondary-500 dark:text-secondary-400">
              {vehicle.year || "-"} · {vehicle.mileage ? `${(vehicle.mileage / 1000).toFixed(0)}k km` : "-"}
            </p>
          </div>
          <p className="shrink-0 text-sm font-bold text-secondary-900 dark:text-secondary-100">
            €{vehicle.price?.toLocaleString("es-ES", { maximumFractionDigits: 0 }) || "-"}
          </p>
        </div>

        <div className="flex items-center justify-between text-xs text-secondary-500 dark:text-secondary-400">
          <span className="truncate">{vehicle.location || "-"}</span>
          <span className="ml-2 shrink-0 uppercase text-[10px] font-semibold tracking-wide text-secondary-400 dark:text-secondary-500">
            {vehicle.source || ""}
          </span>
        </div>

        <div className="flex flex-wrap gap-1.5 border-t border-secondary-100 pt-2 dark:border-secondary-700">
          {opp && (
            <>
              <span className="rounded-full bg-secondary-100 px-2 py-0.5 text-[11px] font-medium text-secondary-700 dark:bg-secondary-700 dark:text-secondary-300">
                ROI {opp.roi.toFixed(1)}%
              </span>
              <RecommendationBadge recommendation={opp.recommendation} label={opp.recommendation_label_es} />
            </>
          )}
          {vehicle.negotiation && (
            <NegotiationBadge recommendation={vehicle.negotiation.recommendation} />
          )}
        </div>
      </div>
    </button>
  );
}
