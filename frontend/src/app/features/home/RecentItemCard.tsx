"use client";

import Link from "next/link";
import { ChevronRight, History } from "lucide-react";

type Props = {
  href: string;
  title: string;
  subtitle?: string | null;
  meta?: string | null;
};

export function RecentItemCard({ href, title, subtitle, meta }: Props) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-2xl border border-secondary-200 bg-white p-4 shadow-sm transition-colors hover:border-primary-300 hover:bg-primary-50/40 dark:border-primary-900/40 dark:bg-secondary-900 dark:hover:border-primary-700/60 dark:hover:bg-primary-900/10"
    >
      <div className="flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-secondary-100 text-secondary-500 dark:bg-secondary-800 dark:text-secondary-300">
        <History className="h-5 w-5" aria-hidden />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-secondary-900 dark:text-secondary-100">
          {title}
        </p>
        {subtitle && (
          <p className="mt-0.5 truncate text-xs text-secondary-500 dark:text-secondary-400">
            {subtitle}
          </p>
        )}
      </div>
      {meta && (
        <span className="flex-none text-xs font-medium text-secondary-500 dark:text-secondary-400">
          {meta}
        </span>
      )}
      <ChevronRight
        className="h-5 w-5 flex-none text-secondary-300 dark:text-secondary-600"
        aria-hidden
      />
    </Link>
  );
}
