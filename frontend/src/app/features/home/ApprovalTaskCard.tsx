"use client";

import Link from "next/link";

type Props = {
  title: string;
  category: string;
  description: string;
  timeLabel?: string;
};

/** Formatea "hace X" a partir de un ISO timestamp, sin librerías extra. */
export function timeAgoEs(iso?: string | null): string | undefined {
  if (!iso) return undefined;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return undefined;
  const diffMs = Date.now() - then;
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "Ahora mismo";
  if (minutes < 60) return `Hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Hace ${hours} h`;
  const days = Math.floor(hours / 24);
  return `Hace ${days} d`;
}

export function ApprovalTaskCard({ title, category, description, timeLabel }: Props) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-secondary-200 bg-white p-3 dark:border-secondary-700 dark:bg-secondary-900">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-sm font-semibold text-secondary-900 dark:text-primary-50">
            {title}
          </p>
          <span className="rounded-full bg-primary-500/15 px-2 py-0.5 text-[10px] font-medium text-primary-600 dark:text-primary-400">
            {category}
          </span>
        </div>
        <p className="mt-0.5 truncate text-xs text-secondary-500 dark:text-secondary-400">
          {description}
        </p>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1.5">
        {timeLabel ? (
          <span className="text-[10px] text-secondary-400">{timeLabel}</span>
        ) : null}
        <Link
          href="/approvals/"
          className="rounded-lg bg-primary-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-primary-700"
        >
          Revisar
        </Link>
      </div>
    </div>
  );
}
