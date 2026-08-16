"use client";

import Link from "next/link";
import { LucideIcon, Inbox } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: { label: string; href?: string; onClick?: () => void };
  fullPage?: boolean;
  className?: string;
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  fullPage = false,
  className = "",
}: EmptyStateProps) {
  const wrapperClass = fullPage
    ? "flex flex-col items-center justify-center min-h-[60vh] px-4"
    : "flex flex-col items-center justify-center py-12 px-4";

  return (
    <div className={`${wrapperClass} ${className}`}>
      <div className="w-14 h-14 rounded-full bg-[#16161f] border border-[#1e1e2d] flex items-center justify-center mb-3">
        <Icon className="h-7 w-7 text-secondary-500" />
      </div>
      <h3 className="text-base font-semibold text-white mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-secondary-400 text-center max-w-xs mb-4">{description}</p>
      )}
      {action && (
        action.href ? (
          <Link
            href={action.href}
            className="inline-flex items-center justify-center px-4 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold transition-colors"
          >
            {action.label}
          </Link>
        ) : action.onClick ? (
          <button
            onClick={action.onClick}
            className="inline-flex items-center justify-center px-4 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold transition-colors"
          >
            {action.label}
          </button>
        ) : null
      )}
    </div>
  );
}
