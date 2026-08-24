"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { cn } from "@/app/utils/cn";
import { useOpportunityDetail, useApprovePhase } from "@/app/hooks/useOpportunityDetail";
import { PhaseTimeline } from "@/app/components/opportunity/PhaseTimeline";
import { AgentResult } from "@/app/components/opportunity/AgentResult";
import { GeneratedFiles } from "@/app/components/opportunity/GeneratedFiles";
import { ApprovalActions } from "@/app/components/opportunity/ApprovalActions";
import { HumanSupervision } from "@/app/components/opportunity/HumanSupervision";
import { ActivityLog } from "@/app/components/opportunity/ActivityLog";
import { RequestChangesModal } from "@/app/components/opportunity/RequestChangesModal";
import { Skeleton } from "@/app/components/ui/Skeleton";
import { ErrorDisplay } from "@/app/components/ui/ErrorDisplay";
import { ArrowLeft, Copy, FileText, Archive, Activity, Info } from "lucide-react";

const tabs = [
  { id: "summary", label: "Resumen", icon: FileText },
  { id: "phases", label: "Fases", icon: Activity },
  { id: "archives", label: "Archivos", icon: Archive },
  { id: "activity", label: "Actividad", icon: Activity },
  { id: "info", label: "Información", icon: Info },
];

export function OpportunityDetailClient() {
  const params = useParams();
  const id = (params?.id as string) || "";
  const [activeTab, setActiveTab] = useState("phases");
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);

  const { data, isLoading, isError, refetch } = useOpportunityDetail(id);
  const approveMutation = useApprovePhase();

  const raw: any = data;
  // Normalizar backend -> frontend (vehicle anidado, score/profit en root)
  const opportunity: any = raw ? {
    ...raw,
    // Derivados para compatibilidad con UI legacy
    title: raw.vehicle ? `${raw.vehicle.brand || ""} ${raw.vehicle.model || ""}`.trim() || `Oportunidad ${raw.id.slice(0,8)}` : raw.title || `Oportunidad ${raw.id.slice(0,8)}`,
    brand: raw.vehicle?.brand ?? raw.brand ?? "",
    model: raw.vehicle?.model ?? raw.model ?? "",
    year: raw.vehicle?.year ?? raw.year ?? null,
    price: raw.vehicle?.price ?? raw.price ?? null,
    market_price: raw.market_price ?? raw.estimated_profit ?? null,
    margin: raw.margin ?? raw.roi_percentage ?? null,
    status: raw.status ?? (raw.recommendation ? (raw.recommendation === "BUY_NOW" ? "active" : raw.recommendation === "REJECT" ? "aborted" : "pending") : "pending"),
    files: raw.files ?? [],
    activity_log: raw.activity_log ?? [],
  } : null;

  const currentPhase = opportunity?.phases?.find((p: any) => p.status === "pending_approval");
  const currentPhaseId = currentPhase?.id;

  const handleApprove = async () => {
    if (!currentPhaseId) return;
    await approveMutation.mutateAsync({ opportunityId: id, phaseId: currentPhaseId, action: "approve" });
  };

  const handleReject = async () => {
    if (!currentPhaseId) return;
    await approveMutation.mutateAsync({ opportunityId: id, phaseId: currentPhaseId, action: "reject" });
  };

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-10 w-full rounded-xl" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <Skeleton className="h-[400px] rounded-2xl" />
            <Skeleton className="h-[200px] rounded-2xl" />
          </div>
          <Skeleton className="h-[300px] rounded-2xl" />
        </div>
      </div>
    );
  }

  if (isError || !opportunity) {
    return (
      <div className="max-w-5xl mx-auto">
        <ErrorDisplay
          title="Error al cargar oportunidad"
          message="No se pudo obtener el detalle de esta oportunidad."
          onRetry={refetch}
        />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            href="/opportunities"
            className="inline-flex items-center gap-1.5 text-xs text-secondary-500 hover:text-primary-400 transition-colors mb-3"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Volver
          </Link>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold text-white">{opportunity.title}</h1>
            <span className={cn(
              "px-2.5 py-0.5 rounded-full text-xs font-bold border",
              opportunity.status === "active" ? "bg-green-400/10 border-green-400/20 text-green-400" :
              opportunity.status === "completed" ? "bg-blue-400/10 border-blue-400/20 text-blue-400" :
              opportunity.status === "aborted" ? "bg-red-400/10 border-red-400/20 text-red-400" :
              "bg-yellow-400/10 border-yellow-400/20 text-yellow-400"
            )}>
              {opportunity.status === "active" ? "Activa" : opportunity.status === "completed" ? "Completada" : opportunity.status === "aborted" ? "Abortada" : "Pendiente"}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1.5">
            <span className="text-[11px] text-secondary-500 font-mono">ID: {opportunity.id}</span>
            <button
              onClick={() => navigator.clipboard.writeText(opportunity.id)}
              className="p-1 rounded text-secondary-600 hover:text-primary-400 transition-colors"
            >
              <Copy className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 p-1 rounded-xl bg-[#16161f] border border-[#1e1e2d] overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all",
                isActive
                  ? "bg-primary-600 text-white shadow-lg shadow-primary-600/20"
                  : "text-secondary-400 hover:text-white hover:bg-[#1e1e2d]"
              )}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {activeTab === "phases" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <div className="rounded-2xl bg-[#111118] border border-[#1e1e2d] p-4">
              <h3 className="text-sm font-semibold text-white mb-4">Fases del workflow</h3>
              <PhaseTimeline
                phases={opportunity.phases}
                opportunityId={id}
                onPhaseAction={refetch}
              />
            </div>

            {opportunity.agent_result && (
              <AgentResult
                confidence={opportunity.agent_result.confidence}
                suggestion={opportunity.agent_result.suggestion}
                explanation={opportunity.agent_result.explanation}
                keyData={opportunity.agent_result.key_data}
              />
            )}

            {opportunity.files && opportunity.files.length > 0 && (
              <div className="rounded-2xl bg-[#111118] border border-[#1e1e2d] p-4">
                <GeneratedFiles files={opportunity.files} />
              </div>
            )}
          </div>

          <div className="space-y-4">
            {currentPhase && (
              <div className="rounded-2xl bg-[#111118] border border-[#1e1e2d] p-4">
                <h3 className="text-sm font-semibold text-white mb-4">Acción requerida</h3>
                <ApprovalActions
                  onApprove={handleApprove}
                  onReject={handleReject}
                  onRequestChanges={() => setShowFeedbackModal(true)}
                  isLoading={approveMutation.isPending}
                />
              </div>
            )}

            <HumanSupervision />
          </div>
        </div>
      )}

      {activeTab === "archives" && (
        <div className="rounded-2xl bg-[#111118] border border-[#1e1e2d] p-4">
          {opportunity.files && opportunity.files.length > 0 ? (
            <GeneratedFiles files={opportunity.files} />
          ) : (
            <div className="text-center py-8">
              <p className="text-sm text-secondary-500">No hay archivos generados aún</p>
            </div>
          )}
        </div>
      )}

      {activeTab === "activity" && (
        <div className="rounded-2xl bg-[#111118] border border-[#1e1e2d] p-4">
          <ActivityLog items={opportunity.activity_log} />
        </div>
      )}

      {activeTab === "summary" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="rounded-2xl bg-[#111118] border border-[#1e1e2d] p-4 space-y-4">
            <h3 className="text-sm font-semibold text-white">Información general</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-xl bg-[#16161f]">
                <p className="text-[11px] text-secondary-500 uppercase">Marca</p>
                <p className="text-sm font-semibold text-white">{opportunity.brand}</p>
              </div>
              <div className="p-3 rounded-xl bg-[#16161f]">
                <p className="text-[11px] text-secondary-500 uppercase">Modelo</p>
                <p className="text-sm font-semibold text-white">{opportunity.model}</p>
              </div>
              <div className="p-3 rounded-xl bg-[#16161f]">
                <p className="text-[11px] text-secondary-500 uppercase">Año</p>
                <p className="text-sm font-semibold text-white">{opportunity.year}</p>
              </div>
              <div className="p-3 rounded-xl bg-[#16161f]">
                <p className="text-[11px] text-secondary-500 uppercase">Precio</p>
                <p className="text-sm font-semibold text-white">${opportunity.price?.toLocaleString()}</p>
              </div>
            </div>
          </div>
          <div className="rounded-2xl bg-[#111118] border border-[#1e1e2d] p-4 space-y-4">
            <h3 className="text-sm font-semibold text-white">Márgenes</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 rounded-xl bg-[#16161f]">
                <span className="text-xs text-secondary-400">Precio de mercado</span>
                <span className="text-sm font-semibold text-white">${opportunity.market_price?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-xl bg-[#16161f]">
                <span className="text-xs text-secondary-400">Margen estimado</span>
                <span className={cn(
                  "text-sm font-bold",
                  opportunity.margin >= 15 ? "text-green-400" : opportunity.margin >= 10 ? "text-yellow-400" : "text-red-400"
                )}>
                  {opportunity.margin}%
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "info" && (
        <div className="rounded-2xl bg-[#111118] border border-[#1e1e2d] p-4">
          <h3 className="text-sm font-semibold text-white mb-4">Información técnica</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between py-2 border-b border-[#1e1e2d]">
              <span className="text-secondary-400">ID de oportunidad</span>
              <span className="text-white font-mono text-xs">{opportunity.id}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#1e1e2d]">
              <span className="text-secondary-400">Estado</span>
              <span className="text-white capitalize">{opportunity.status}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#1e1e2d]">
              <span className="text-secondary-400">Fase actual</span>
              <span className="text-white">{opportunity.phases?.find((p: any) => p.status === "pending_approval" || p.status === "in_progress")?.title || "Completado"}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#1e1e2d]">
              <span className="text-secondary-400">Total fases</span>
              <span className="text-white">{opportunity.phases?.length || 0}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#1e1e2d]">
              <span className="text-secondary-400">Fases completadas</span>
              <span className="text-white">{opportunity.phases?.filter((p: any) => p.status === "completed").length || 0}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-secondary-400">Archivos generados</span>
              <span className="text-white">{opportunity.files?.length || 0}</span>
            </div>
          </div>
        </div>
      )}

      {/* Feedback Modal */}
      <RequestChangesModal
        open={showFeedbackModal}
        onClose={() => setShowFeedbackModal(false)}
        opportunityId={id}
        phaseId={currentPhaseId || ""}
      />
    </div>
  );
}
