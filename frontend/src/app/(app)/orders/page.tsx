"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { searchOrdersService } from "@/app/services/search-orders";
import type { SearchOrder, SearchOrderStatus } from "@/app/types/search-orders";

const STATUS_LABEL: Record<SearchOrderStatus, string> = {
  PENDING: "Pendiente",
  RUNNING: "En ejecución",
  COMPLETED: "Completada",
  FAILED: "Fallida",
};

const STATUS_STYLE: Record<SearchOrderStatus, string> = {
  PENDING: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  RUNNING: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
  COMPLETED: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  FAILED: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
};

function formatEur(value: number | null): string {
  if (value == null) return "—";
  return `${new Intl.NumberFormat("es-ES").format(Math.round(value))} €`;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("es-ES", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function OrdersPage() {
  const queryClient = useQueryClient();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: orders, isLoading, error } = useQuery<SearchOrder[]>({
    queryKey: ["search-orders"],
    queryFn: searchOrdersService.list,
    refetchInterval: 15000,
  });

  const markSeenMutation = useMutation({
    mutationFn: searchOrdersService.markSeen,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["search-orders"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await searchOrdersService.remove(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["search-orders"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });
    },
  });

  if (isLoading) {
    return <div className="p-6">Cargando búsquedas...</div>;
  }

  if (error) {
    return <div className="p-6 text-red-600">Error al cargar las búsquedas.</div>;
  }

  const list = orders ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            Búsquedas
          </h1>
          <p className="text-secondary-500 dark:text-secondary-400">
            Tus búsquedas en segundo plano y sus resultados
          </p>
        </div>
        <Link
          href="/search"
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Nueva búsqueda
        </Link>
      </div>

      {list.length === 0 ? (
        <div className="rounded-lg border border-dashed border-secondary-300 p-8 text-center text-secondary-500 dark:border-secondary-700">
          Aún no tienes búsquedas. Lanza una desde{" "}
          <Link href="/search" className="text-blue-600 hover:underline">
            nueva búsqueda
          </Link>
          .
        </div>
      ) : (
        <div className="space-y-3">
          {list.map((order) => (
            <div
              key={order.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-secondary-200 bg-white p-4 dark:border-secondary-700 dark:bg-secondary-800"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Link
                    href={`/orders/detail/?id=${order.id}`}
                    className="truncate font-medium text-secondary-900 hover:text-blue-600 dark:text-secondary-100"
                  >
                    {order.query}
                  </Link>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[order.status]}`}
                  >
                    {STATUS_LABEL[order.status]}
                  </span>
                  {order.new_count > 0 && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                      {order.new_count} nuevos
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-secondary-500 dark:text-secondary-400">
                  {order.results_count} resultados · Presupuesto máx.{" "}
                  {formatEur(order.max_purchase_price)} · Creada{" "}
                  {formatDate(order.created_at)}
                </p>
                {order.status === "FAILED" && order.error_message && (
                  <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                    {order.error_message.slice(0, 200)}
                  </p>
                )}
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <Link
                  href={`/orders/detail/?id=${order.id}`}
                  className="rounded-md border border-secondary-300 bg-white px-3 py-1.5 text-sm font-medium text-secondary-700 hover:bg-secondary-50 dark:border-secondary-600 dark:bg-secondary-700 dark:text-secondary-100"
                >
                  Ver
                </Link>
                {order.new_count > 0 && (
                  <button
                    onClick={() => markSeenMutation.mutate(order.id)}
                    disabled={markSeenMutation.isPending}
                    className="rounded-md bg-amber-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50"
                  >
                    Marcar vistos
                  </button>
                )}
                <button
                  onClick={() => {
                    setDeletingId(order.id);
                    deleteMutation.mutate(order.id);
                  }}
                  disabled={deleteMutation.isPending && deletingId === order.id}
                  className="rounded-md bg-red-50 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-100 disabled:opacity-50 dark:bg-red-900/30 dark:text-red-300"
                >
                  Eliminar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
