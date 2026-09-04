"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Briefcase,
  Bot,
  CheckSquare,
  LayoutGrid,
  type LucideIcon,
} from "lucide-react";
import { useApprovals } from "@/app/hooks/useApprovals";
import { isActiveRoute } from "@/app/utils/is-active-route";

type Tab = {
  href: string;
  label: string;
  Icon: LucideIcon;
  /** Insignia con un conteo real (no decorativa). */
  badgeCount?: number;
  /** Botón central destacado (como el acceso a Agentes en el diseño). */
  featured?: boolean;
};

/**
 * MOBILE.SHELL.1 — Barra de navegación inferior (5 destinos, pulgar).
 * Solo se renderiza en móvil desde AppShell.
 */
export function MobileTabBar() {
  const pathname = usePathname();
  const { data: approvals } = useApprovals();
  const pendingApprovals = approvals?.length ?? 0;

  const tabs: Tab[] = [
    { href: "/dashboard/", label: "Dashboard", Icon: LayoutDashboard },
    { href: "/opportunities/", label: "Oport.", Icon: Briefcase },
    { href: "/agents/", label: "Agentes", Icon: Bot, featured: true },
    {
      href: "/approvals/",
      label: "Aprob.",
      Icon: CheckSquare,
      badgeCount: pendingApprovals,
    },
    { href: "/more/", label: "Más", Icon: LayoutGrid },
  ];

  // Rutas alcanzables SOLO desde "Más" (ver more/page.tsx): sin esto,
  // ningún tab queda marcado como activo mientras se navega por ellas —
  // el usuario pierde la referencia de "dónde estoy" en cuanto sale de
  // los 5 destinos directos.
  const MORE_SUB_ROUTES = [
    "/vehicles/",
    "/deals/",
    "/inspection/",
    "/workflows/",
    "/history/",
    "/api-keys/",
    "/settings/",
    "/admin/",
  ];
  const onMoreSubRoute = MORE_SUB_ROUTES.some((r) => isActiveRoute(pathname, r));

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-secondary-200 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur dark:border-primary-900/40 dark:bg-secondary-950/95"
      aria-label="Navegación principal"
    >
      <ul className="flex h-16 items-stretch justify-around">
        {tabs.map((tab) => {
          const active =
            isActiveRoute(pathname, tab.href) ||
            (tab.href === "/more/" && onMoreSubRoute);

          if (tab.featured) {
            return (
              <li key={tab.href} className="relative flex-1">
                <Link
                  href={tab.href}
                  aria-current={active ? "page" : undefined}
                  className="flex h-full flex-col items-center justify-center gap-0.5"
                >
                  <span
                    className={`-mt-6 flex h-12 w-12 items-center justify-center rounded-full shadow-lg shadow-primary-900/30 transition-colors ${
                      active
                        ? "bg-primary-600 text-white"
                        : "bg-primary-500 text-white"
                    }`}
                  >
                    <tab.Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <span
                    className={`text-[10px] font-medium ${
                      active
                        ? "text-primary-600 dark:text-primary-400"
                        : "text-secondary-500 dark:text-secondary-400"
                    }`}
                  >
                    {tab.label}
                  </span>
                </Link>
              </li>
            );
          }

          return (
            <li key={tab.href} className="relative flex-1">
              <Link
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={`relative flex h-full flex-col items-center justify-center gap-0.5 text-[10px] font-medium ${
                  active
                    ? "text-primary-600 dark:text-primary-400"
                    : "text-secondary-500 dark:text-secondary-400"
                }`}
              >
                {active && (
                  <span className="absolute top-0 h-0.5 w-6 rounded-full bg-primary-500" />
                )}
                <tab.Icon
                  className="h-5 w-5"
                  strokeWidth={active ? 2.2 : 1.8}
                  aria-hidden
                />
                {tab.label}
              </Link>
              {!!tab.badgeCount && (
                <span className="absolute right-[calc(50%-20px)] top-1 rounded-full bg-red-500 px-1.5 py-0.5 text-[9px] font-bold leading-tight text-white">
                  {tab.badgeCount > 99 ? "99+" : tab.badgeCount}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
