"use client";

import { cn } from "@/app/utils/cn";

interface ScoreBadgeProps {
  score: number;
  label?: string;
  size?: "sm" | "md" | "lg";
}

function getScoreColor(score: number): string {
  if (score >= 80) return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
  if (score >= 60) return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400";
  if (score >= 40) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400";
  return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";
}

export function ScoreBadge({ score, label, size = "sm" }: ScoreBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium",
        {
          "px-2 py-0.5 text-xs": size === "sm",
          "px-2.5 py-1 text-sm": size === "md",
          "px-3 py-1.5 text-base": size === "lg",
        },
        getScoreColor(score)
      )}
    >
      {label && <span className="mr-1">{label}:</span>}
      {score}
    </span>
  );
}

export function ProfitBadge({ value, size = "sm" }: { value: number; size?: "sm" | "md" | "lg" }) {
  const color = value >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400";
  return (
    <span className={cn("font-semibold", color, {
      "text-xs": size === "sm",
      "text-sm": size === "md",
      "text-base": size === "lg",
    })}>
      {value >= 0 ? "+" : ""}€{value.toLocaleString("es-ES", { maximumFractionDigits: 0 })}
    </span>
  );
}

export function OpportunityBadge({
  level,
  size = "sm",
}: {
  level: string;
  size?: "sm" | "md" | "lg";
}) {
  const config: Record<string, { color: string; label: string }> = {
    EXCELLENT: { color: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400", label: "Excelente" },
    GOOD: { color: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400", label: "Buena" },
    AVERAGE: { color: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400", label: "Media" },
    POOR: { color: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400", label: "Baja" },
    REJECT: { color: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400", label: "Rechazado" },
  };

  const c = config[level] || config.POOR;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium",
        {
          "px-2 py-0.5 text-xs": size === "sm",
          "px-2.5 py-1 text-sm": size === "md",
          "px-3 py-1.5 text-base": size === "lg",
        },
        c.color
      )}
    >
      {c.label}
    </span>
  );
}

export function NegotiationBadge({
  recommendation,
  size = "sm",
}: {
  recommendation: string;
  size?: "sm" | "md" | "lg";
}) {
  const config: Record<string, { color: string; label: string }> = {
    BUY: { color: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400", label: "Comprar" },
    NEGOTIATE: { color: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400", label: "Negociar" },
    WALK_AWAY: { color: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400", label: "Abandonar" },
  };

  const c = config[recommendation] || { color: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400", label: recommendation };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium",
        {
          "px-2 py-0.5 text-xs": size === "sm",
          "px-2.5 py-1 text-sm": size === "md",
          "px-3 py-1.5 text-base": size === "lg",
        },
        c.color
      )}
    >
      {c.label}
    </span>
  );
}

export function RecommendationBadge({
  recommendation,
  label,
  size = "sm",
}: {
  recommendation: string;
  label?: string | null;
  size?: "sm" | "md" | "lg";
}) {
  const config: Record<string, { color: string; label: string }> = {
    BUY_NOW: { color: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400", label: "Comprar ahora" },
    WATCH: { color: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400", label: "Vigilar" },
    NEGOTIATE: { color: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400", label: "Negociar" },
    REJECT: { color: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400", label: "Rechazar" },
    BUY: { color: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400", label: "Comprar" },
    CONSIDER: { color: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400", label: "Considerar" },
  };

  const c = config[recommendation] || { color: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400", label: recommendation };
  const displayLabel = label || c.label;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium",
        {
          "px-2 py-0.5 text-xs": size === "sm",
          "px-2.5 py-1 text-sm": size === "md",
          "px-3 py-1.5 text-base": size === "lg",
        },
        c.color
      )}
    >
      {displayLabel}
    </span>
  );
}