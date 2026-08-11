"use client";

import Link from "next/link";
import { ChevronRight, Sparkles } from "lucide-react";
import { cn } from "@/app/utils/cn";

export type BadgeTone =
  | "success"
  | "info"
  | "warning"
  | "danger"
  | "neutral";

const toneClasses: Record<BadgeTone, string> = {
  success: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  info: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  warning: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  danger: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  neutral: "bg-secondary-100 text-secondary-700 dark:bg-secondary-800 dark:text-secondary-300",
};

type Props = {
  href: string;
  title: string;
  subtitle?: string | null;
  badge?: { label: string; tone?: BadgeTone } | null;
  meta?: string | null;
};

export function OpportunityTeaserCard({
  href,
  title,
  subtitle,
  badge,
  meta,
}: Props) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-2xl border border-secondary-200 bg-white p-4 shadow-sm transition-colors hover:border-primary-300 hover:bg-primary-50/40 dark:border-primary-900/40 dark:bg-secondary-900 dark:hover:border-primary-700/60 dark:hover:bg-primary-900/10"
    >
      <div className="flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-primary-100 text-primary-600 dark:bg-primary-900/40 dark:text-primary-300">
        <Sparkles className="h-5 w-5" aria-hidden />
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
        {meta && (
          <p className="mt-0.5 text-xs font-medium text-primary-600 dark:text-primary-400">
            {meta}
          </p>
        )}
      </div>
      {badge && (
        <span
          className={cn(
            "inline-flex flex-none items-center rounded-full px-2 py-0.5 text-xs font-medium",
            toneClasses[badge.tone ?? "neutral"]
          )}
        >
          {badge.label}
        </span>
      )}
      <ChevronRight
        className="h-5 w-5 flex-none text-secondary-300 dark:text-secondary-600"
        aria-hidden
      />
    </Link>
  );
}
