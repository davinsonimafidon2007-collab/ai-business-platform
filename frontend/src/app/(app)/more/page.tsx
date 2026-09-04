"use client";

import Link from "next/link";
import {
  Search,
  Car,
  Handshake,
  SearchCheck,
  Workflow,
  History,
  KeyRound,
  Settings,
  Bot,
  Shield,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";
import { useAuthStore } from "@/app/store/auth-store";
import { isAuthDisabled } from "@/app/config/app-mode";

type MoreLink = { href: string; label: string; Icon: LucideIcon };

// Bug real: Búsqueda, Deals, Agentes (fuera del tab central), Workflows y
// Configuración no tenían NINGÚN punto de entrada en móvil (ni en la
// barra inferior ni aquí) — inalcanzables salvo escribiendo la URL a mano.
const MAIN_LINKS: MoreLink[] = [
  { href: "/search/", label: "Búsqueda", Icon: Search },
  { href: "/vehicles/", label: "Mis vehículos", Icon: Car },
  { href: "/deals/", label: "Deals", Icon: Handshake },
  { href: "/inspection/", label: "Inspección", Icon: SearchCheck },
  { href: "/agents/", label: "Agentes", Icon: Bot },
  { href: "/workflows/", label: "Workflows", Icon: Workflow },
  { href: "/history/", label: "Historial", Icon: History },
  { href: "/api-keys/", label: "API keys", Icon: KeyRound },
  { href: "/settings/", label: "Configuración", Icon: Settings },
];

const ADMIN_LINKS: MoreLink[] = [
  { href: "/admin/", label: "Admin", Icon: Shield },
];

/**
 * MOBILE.SHELL.1 — Pantalla "Más": agrupa los destinos que no caben en los
 * 5 tabs. Estilo lista tipo settings (filas táctiles altas), no sidebar.
 */
export default function MorePage() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === "admin" || isAuthDisabled();
  const links: MoreLink[] = isAdmin
    ? [...MAIN_LINKS, ...ADMIN_LINKS]
    : MAIN_LINKS;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
          Más
        </h1>
        <p className="text-secondary-500 dark:text-secondary-400">
          Herramientas y gestión de la cuenta
        </p>
      </div>

      <nav
        aria-label="Más opciones"
        className="overflow-hidden rounded-xl border border-secondary-200 bg-white shadow-sm dark:border-secondary-700 dark:bg-secondary-900"
      >
        <ul className="divide-y divide-secondary-100 dark:divide-secondary-800">
          {links.map(({ href, label, Icon }) => (
            <li key={href}>
              <Link
                href={href}
                className="flex min-h-[52px] items-center gap-3 px-4 text-sm font-medium text-secondary-700 transition-colors hover:bg-secondary-50 dark:text-secondary-300 dark:hover:bg-secondary-800"
              >
                <Icon
                  className="h-5 w-5 text-primary-600 dark:text-primary-400"
                  aria-hidden
                />
                <span className="flex-1">{label}</span>
                <ChevronRight
                  className="h-4 w-4 text-secondary-400"
                  aria-hidden
                />
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}