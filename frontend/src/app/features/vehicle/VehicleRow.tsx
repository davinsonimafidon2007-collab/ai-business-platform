"use client";

import { cn } from "@/app/utils/cn";
import { ScoreBadge, ProfitBadge, OpportunityBadge, RecommendationBadge } from "@/app/components/ui/ScoreBadge";
import type { SearchResultItem } from "@/app/types/vehicle";

interface VehicleRowProps {
  vehicle: SearchResultItem;
  onClick: () => void;
  isSelected?: boolean;
}

export function VehicleRow({ vehicle, onClick, isSelected }: VehicleRowProps) {
  const opp = vehicle.opportunity;
  const score = vehicle.vehicle_score;

  return (
    <tr
      onClick={onClick}
      className={cn(
        "cursor-pointer border-b border-secondary-200 transition-colors hover:bg-secondary-50 dark:border-secondary-700 dark:hover:bg-secondary-800",
        isSelected && "bg-primary-50 dark:bg-primary-900/20"
      )}
    >
      <td className="px-3 py-2">
        {vehicle.images && vehicle.images[0] ? (
          <img
            src={vehicle.images[0]}
            alt={`${vehicle.brand} ${vehicle.model}`}
            className="h-14 w-20 rounded object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='56' viewBox='0 0 80 56'%3E%3Crect width='80' height='56' fill='%23e5e7eb'/%3E%3Ctext x='40' y='28' text-anchor='middle' dy='.3em' fill='%239ca3af' font-size='10'%3ESin imagen%3C/text%3E%3C/svg%3E";
            }}
          />
        ) : (
          <div className="flex h-14 w-20 items-center justify-center rounded bg-secondary-100 text-xs text-secondary-400 dark:bg-secondary-700">
            Sin imagen
          </div>
        )}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-sm font-medium text-secondary-900 dark:text-secondary-100">
        {vehicle.brand || "-"}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-sm text-secondary-600 dark:text-secondary-400">
        {vehicle.model || "-"}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-sm text-secondary-600 dark:text-secondary-400">
        {vehicle.year || "-"}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-sm text-secondary-600 dark:text-secondary-400">
        {vehicle.mileage ? `${(vehicle.mileage / 1000).toFixed(0)}k km` : "-"}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-sm font-medium text-secondary-900 dark:text-secondary-100">
        €{vehicle.price?.toLocaleString("es-ES", { maximumFractionDigits: 0 }) || "-"}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-sm text-secondary-600 dark:text-secondary-400">
        {vehicle.location || "-"}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-sm text-secondary-600 dark:text-secondary-400">
        {vehicle.source || "-"}
      </td>
      <td className="whitespace-nowrap px-3 py-2">
        {score && <ScoreBadge score={score.score} />}
      </td>
      <td className="whitespace-nowrap px-3 py-2">
        {opp && <ScoreBadge score={Math.round(opp.overall_score)} />}
      </td>
      <td className="whitespace-nowrap px-3 py-2">
        {opp && <span className="text-sm font-medium">{opp.roi.toFixed(1)}%</span>}
      </td>
      <td className="whitespace-nowrap px-3 py-2">
        {opp && <ProfitBadge value={opp.estimated_profit} />}
      </td>
      <td className="whitespace-nowrap px-3 py-2">
        {opp && <OpportunityBadge level={opp.opportunity_level} />}
      </td>
      <td className="whitespace-nowrap px-3 py-2">
        {opp && <RecommendationBadge recommendation={opp.recommendation} />}
      </td>
    </tr>
  );
}