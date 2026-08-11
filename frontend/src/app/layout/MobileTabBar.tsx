"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  Search,
  Sparkles,
  Handshake,
  LayoutGrid,
  type LucideIcon,
} from "lucide-react";

const TABS: { href: string; label: string; Icon: LucideIcon }[] = [
  { href: "/dashboard/", label: "Inicio", Icon: Home },
  { href: "/search/", label: "Buscar", Icon: Search },
  { href: "/opportunities/", label: "Oport.", Icon: Sparkles },
  { href: "/deals/", label: "Deals", Icon: Handshake },
  { href: "/more/", label: "Más", Icon: LayoutGrid },
];

/**
 * MOBILE.SHELL.1 — Barra de navegación inferior (5 destinos, pulgar).
 * Solo se renderiza en móvil desde AppShell.
 */
export function MobileTabBar() {
  const pathname = usePathname();

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-secondary-200 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur dark:border-primary-900/40 dark:bg-secondary-950/95"
      aria-label="Navegación principal"
    >
      <ul className="flex h-14 items-stretch justify-around">
        {TABS.map((tab) => {
          const active =
            pathname === tab.href || pathname.startsWith(tab.href);
          return (
            <li key={tab.href} className="flex-1">
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
            </li>
          );
        })}
      </ul>
    </nav>
  );
}