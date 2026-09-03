"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Search,
  Car,
  Briefcase,
  Handshake,
  ScanEye,
  Bot,
  CheckSquare,
  Workflow,
  KeyRound,
  History,
  Shield,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/app/utils/cn";
import { useAuthStore } from "@/app/store/auth-store";
import { useApprovals } from "@/app/hooks/useApprovals";

type NavItem = { name: string; href: string; icon: LucideIcon; badgeCount?: number };

export function Sidebar() {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const { data: approvals } = useApprovals();
  const pendingApprovals = approvals?.length ?? 0;

  const navigation: NavItem[] = [
    { name: "Dashboard", href: "/dashboard/", icon: LayoutDashboard },
    { name: "Búsqueda", href: "/search/", icon: Search },
    { name: "Vehículos", href: "/vehicles/", icon: Car },
    { name: "Oportunidades", href: "/opportunities/", icon: Briefcase },
    { name: "Deals", href: "/deals/", icon: Handshake },
    { name: "Inspección", href: "/inspection/", icon: ScanEye },
    { name: "Agentes", href: "/agents/", icon: Bot },
    {
      name: "Aprobaciones",
      href: "/approvals/",
      icon: CheckSquare,
      badgeCount: pendingApprovals,
    },
    { name: "Workflows", href: "/workflows/", icon: Workflow },
    { name: "API keys", href: "/api-keys/", icon: KeyRound },
    { name: "Historial", href: "/history/", icon: History },
  ];

  const adminNavigation: NavItem[] = [
    { name: "Admin", href: "/admin/", icon: Shield },
    { name: "Admin API keys", href: "/admin/api-keys/", icon: ShieldCheck },
  ];

  const items = user?.role === "admin" ? [...navigation, ...adminNavigation] : navigation;

  return (
    <aside className="fixed left-0 top-0 z-40 hidden h-screen w-64 border-r border-secondary-200 bg-white md:flex md:flex-col dark:border-secondary-700 dark:bg-secondary-900">
      <div className="flex h-16 shrink-0 items-center border-b border-secondary-200 px-6 dark:border-secondary-700">
        <Link href="/dashboard/" className="text-lg font-bold text-primary-600 dark:text-primary-400">
          AI Business
        </Link>
      </div>
      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-4">
        {items.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400"
                  : "text-secondary-600 hover:bg-secondary-50 dark:text-secondary-400 dark:hover:bg-secondary-800"
              )}
            >
              <span className="flex items-center gap-3">
                <item.icon className="h-[18px] w-[18px]" aria-hidden />
                {item.name}
              </span>
              {!!item.badgeCount && (
                <span className="rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                  {item.badgeCount > 99 ? "99+" : item.badgeCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
