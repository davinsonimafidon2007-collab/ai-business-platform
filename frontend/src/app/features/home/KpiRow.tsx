"use client";

import type { LucideIcon } from "lucide-react";

type Tone = "primary" | "success" | "warning" | "info";

const TONE_CLASSES: Record<Tone, string> = {
  primary: "bg-primary-500/15 text-primary-500 dark:text-primary-400",
  success: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  warning: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  info: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
};

type Kpi = {
  label: string;
  value: string | number;
  hint?: string;
  icon?: LucideIcon;
  tone?: Tone;
};

export function KpiRow({ items }: { items: Kpi[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {items.map((k) => (
        <div
          key={k.label}
          className="rounded-2xl border border-secondary-200 bg-white p-4 shadow-sm dark:border-primary-900/40 dark:bg-secondary-900 dark:ring-1 dark:ring-primary-900/20"
        >
          {k.icon ? (
            <span
              className={`mb-2 inline-flex h-9 w-9 items-center justify-center rounded-xl ${TONE_CLASSES[k.tone ?? "primary"]}`}
            >
              <k.icon className="h-4.5 w-4.5" aria-hidden />
            </span>
          ) : null}
          <p className="text-2xl font-semibold text-secondary-900 dark:text-primary-50">
            {k.value}
          </p>
          <p className="mt-1 text-xs font-medium text-secondary-600 dark:text-secondary-300">
            {k.label}
          </p>
          {k.hint ? (
            <p className="mt-0.5 text-[10px] text-secondary-400">{k.hint}</p>
          ) : null}
        </div>
      ))}
    </div>
  );
}
