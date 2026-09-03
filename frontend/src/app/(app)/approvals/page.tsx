"use client";

import { useState, useMemo } from "react";
import { useApprovals } from "@/app/hooks/useApprovals";
import { useApprovePhase } from "@/app/hooks/useOpportunityDetail";
import { ApprovalReviewCard } from "@/app/components/approvals/ApprovalReviewCard";
import { ApprovalDetailDrawer } from "@/app/components/approvals/ApprovalDetailDrawer";
import { timeAgoEs } from "@/app/features/home/ApprovalTaskCard";
import { Skeleton } from "@/app/components/ui/Skeleton";
import { ErrorDisplay } from "@/app/components/ui/ErrorDisplay";
import { EmptyState } from "@/app/components/ui/EmptyState";

const FILTERS = ["Todas", "Negociación", "Documentación", "Análisis", "Revisión"];

export default function ApprovalsPage() {
  const [activeFilter, setActiveFilter] = useState("Todas");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data, isLoading, isError, refetch } = useApprovals();
  const approveMutation = useApprovePhase();

  const filtered = useMemo(() => {
    const approvalsData = data ?? [];
    if (activeFilter === "Todas") return approvalsData;
    return approvalsData.filter((a: any) => a.category === activeFilter);
  }, [data, activeFilter]);

  const selectedApproval = filtered.find((a: any) => a.id === selectedId);

  const detailData = selectedApproval
    ? {
        title: selectedApproval.title,
        subtitle: `${selectedApproval.category} · ${selectedApproval.status === "pending" ? "Pendiente de aprobación" : selectedApproval.status}`,
        status: selectedApproval.status === "pending" ? "Pendiente de aprobación" : selectedApproval.status,
        explanation: selectedApproval.description || "Sin descripción disponible.",
      }
    : undefined;

  const handleApprove = async () => {
    if (!selectedApproval) return;
    await approveMutation.mutateAsync({
      opportunityId: selectedApproval.opportunity_id,
      phaseId: selectedApproval.id,
      action: "approve",
    });
    setSelectedId(null);
  };

  const handleReject = async () => {
    if (!selectedApproval) return;
    await approveMutation.mutateAsync({
      opportunityId: selectedApproval.opportunity_id,
      phaseId: selectedApproval.id,
      action: "reject",
    });
    setSelectedId(null);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white">Aprobaciones pendientes</h1>
        <p className="text-sm text-secondary-500 mt-0.5">
          {isLoading ? "Cargando..." : `${filtered.length} tareas requieren tu decisión`}
        </p>
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
          {filtered.map((item: any) => (
            <ApprovalReviewCard
              key={item.id}
              title={item.title}
              category={item.category}
              description={item.description}
              detail={item.detail}
              time={timeAgoEs(item.created_at) ?? "—"}
              image={item.image}
              onReview={() => setSelectedId(item.id)}
            />
          ))}
        </div>
      )}

      <ApprovalDetailDrawer
        open={selectedId !== null}
        onClose={() => setSelectedId(null)}
        onApprove={handleApprove}
        onReject={handleReject}
        isSubmitting={approveMutation.isPending}
        data={detailData}
      />
    </div>
  );
}
