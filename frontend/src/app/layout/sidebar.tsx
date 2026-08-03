"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/app/utils/cn";

const navigation = [
  { name: "Dashboard", href: "/dashboard/", icon: "📊" },
  { name: "Búsqueda", href: "/search/", icon: "🔍" },
  { name: "Vehículos", href: "/vehicles/", icon: "🚗" },
  { name: "Oportunidades", href: "/opportunities/", icon: "💼" },
  { name: "Inspección", href: "/inspection/", icon: "🔎" },
  { name: "Historial", href: "/history/", icon: "📋" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-secondary-200 bg-white dark:border-secondary-700 dark:bg-secondary-900">
      <div className="flex h-16 items-center border-b border-secondary-200 px-6 dark:border-secondary-700">
        <Link href="/dashboard/" className="text-lg font-bold text-primary-600">
          AI Business
        </Link>
      </div>
      <nav className="flex flex-col gap-1 p-4">
        {navigation.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400"
                  : "text-secondary-600 hover:bg-secondary-50 dark:text-secondary-400 dark:hover:bg-secondary-800"
              )}
            >
              <span className="text-lg">{item.icon}</span>
              {item.name}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}