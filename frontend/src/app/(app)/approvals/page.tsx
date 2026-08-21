"use client";

import { useState, useMemo } from "react";
import { useApprovals } from "@/app/hooks/useApprovals";
import { ApprovalReviewCard } from "@/app/components/approvals/ApprovalReviewCard";
import { ApprovalDetailDrawer } from "@/app/components/approvals/ApprovalDetailDrawer";
import { Skeleton } from "@/app/components/ui/Skeleton";
import { ErrorDisplay } from "@/app/components/ui/ErrorDisplay";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { SlidersHorizontal } from "lucide-react";

const FILTERS = ["Todas", "Negociación", "Documentación", "Análisis", "Revisión"];

export default function ApprovalsPage() {
  const [activeFilter, setActiveFilter] = useState("Todas");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data, isLoading, isError, refetch } = useApprovals();

  const approvalsData = data ?? [];

  const filtered = useMemo(() => {
    if (activeFilter === "Todas") return approvalsData;
    return approvalsData.filter((a: any) => a.category === activeFilter);
  }, [approvalsData, activeFilter]);

  const selectedApproval = filtered.find((a: any) => a.id === selectedId);

  const detailData = selectedApproval
    ? {
        title: selectedApproval.title,
        subtitle: `${selectedApproval.description} · ${selectedApproval.status === "pending" ? "Pendiente de aprobación" : selectedApproval.status}`,
        status: selectedApproval.status === "pending" ? "Pendiente de aprobación" : selectedApproval.status,
        confidence: selectedApproval.priority === "ALTO" ? "Alta" : selectedApproval.priority === "MEDIO" ? "Media" : "Baja",
        suggestion: "WAIT_FOR_APPROVAL",
        explanation: `El agente ha completado el análisis para ${selectedApproval.title}. Revisa los archivos generados y toma una decisión.`,
        files: [
          { name: `analisis_${selectedApproval.id}.pdf`, type: "pdf" as const, size: "245 KB" },
          { name: `comparativa_${selectedApproval.id}.xlsx`, type: "xlsx" as const, size: "32 KB" },
        ],
      }
    : undefined;

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Aprobaciones pendientes</h1>
          <p className="text-sm text-secondary-500 mt-0.5">
            {isLoading ? "Cargando..." : `${filtered.length} tareas requieren tu decisión`}
          </p>
        </div>
        <button className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[#16161f] border border-[#1e1e2d] text-secondary-300 hover:text-white text-xs font-medium transition-colors">
          <SlidersHorizontal className="w-3.5 h-3.5" />
          Filtrar
        </button>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 lg:mx-0 lg:px-0 scrollbar-hide">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setActiveFilter(f)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
              activeFilter === f
                ? "bg-primary-600 text-white"
                : "bg-[#16161f] border border-[#1e1e2d] text-secondary-400 hover:text-white hover:border-[#2a2a3d]"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 p-3 rounded-2xl bg-[#111118] border border-[#1e1e2d]">
              <Skeleton className="w-16 h-16 rounded-xl shrink-0" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-48" />
              </div>
              <Skeleton className="h-8 w-16 rounded-lg shrink-0" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <ErrorDisplay
          title="Error al cargar aprobaciones"
          message="No se pudieron obtener las aprobaciones."
          onRetry={refetch}
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="Sin aprobaciones pendientes"
          description="No hay tareas que requieran tu decisión."
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((item: any, idx: number) => (
            <ApprovalReviewCard
              key={item.id}
              title={item.title}
              category={item.category}
              description={item.description}
              detail={item.detail}
              time={item.created_at ? `Hace ${((idx * 7) % 50) + 5} min` : "Hace 15 min"}
              image={item.image}
              onReview={() => setSelectedId(item.id)}
            />
          ))}
        </div>
      )}

      <ApprovalDetailDrawer
        open={selectedId !== null}
        onClose={() => setSelectedId(null)}
        data={detailData}
      />
    </div>
  );
}
