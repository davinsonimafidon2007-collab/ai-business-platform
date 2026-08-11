"use client";

type Kpi = { label: string; value: string | number; hint?: string };

export function KpiRow({ items }: { items: Kpi[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {items.map((k) => (
        <div
          key={k.label}
          className="rounded-2xl border border-secondary-200 bg-white p-4 shadow-sm dark:border-primary-900/40 dark:bg-secondary-900 dark:ring-1 dark:ring-primary-900/20"
        >
          <p className="text-2xl font-semibold text-primary-600 dark:text-primary-400">
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
