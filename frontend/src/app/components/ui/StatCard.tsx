"use client";

import { cn } from "@/app/utils/cn";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: string;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

export function StatCard({ title, value, subtitle, icon, trend, className }: StatCardProps) {
  const trendColors = {
    up: "text-green-600 dark:text-green-400",
    down: "text-red-600 dark:text-red-400",
    neutral: "text-secondary-500 dark:text-secondary-400",
  };

  return (
    <div
      className={cn(
        "rounded-lg border border-secondary-200 bg-white p-4 dark:border-secondary-700 dark:bg-secondary-800",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm text-secondary-500 dark:text-secondary-400">{title}</p>
        {icon && <span className="text-xl">{icon}</span>}
      </div>
      <p className="mt-1 text-2xl font-bold text-secondary-900 dark:text-secondary-100">
        {value}
      </p>
      {subtitle && (
        <p className={cn("mt-1 text-xs", trend ? trendColors[trend] : "text-secondary-500")}>
          {subtitle}
        </p>
      )}
    </div>
  );
}