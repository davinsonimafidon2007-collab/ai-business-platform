"use client";

import { cn } from "@/app/utils/cn";
import { Check, Clock, AlertCircle, Loader2 } from "lucide-react";
import { useApprovePhase } from "@/app/hooks/useOpportunityDetail";

import type { Phase, PhaseStatus } from "@/app/hooks/useOpportunityDetail";

export type { PhaseStatus };

interface PhaseTimelineProps {
  phases: Phase[];
  opportunityId: string;
  onPhaseAction?: () => void;
}

/** Fecha legible de la fase: completada > iniciada > nada. */
function phaseTimestamp(phase: Phase): string | null {
  const raw = phase.completed_at ?? phase.started_at;
  if (!raw) return null;
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const statusConfig: Record<PhaseStatus, { icon: typeof Check; color: string; bg: string; label: string }> = {
  completed: { icon: Check, color: "text-green-400", bg: "bg-green-400/10 border-green-400/30", label: "Completado" },
  pending_approval: { icon: AlertCircle, color: "text-yellow-400", bg: "bg-yellow-400/10 border-yellow-400/30", label: "Pendiente de aprobación" },
  in_progress: { icon: Loader2, color: "text-primary-400", bg: "bg-primary-400/10 border-primary-400/30", label: "En ejecución" },
  pending: { icon: Clock, color: "text-secondary-500", bg: "bg-secondary-500/10 border-secondary-500/20", label: "Pendiente" },
  aborted: { icon: AlertCircle, color: "text-red-400", bg: "bg-red-400/10 border-red-400/30", label: "Abortado" },
};

export function PhaseTimeline({ phases, opportunityId, onPhaseAction }: PhaseTimelineProps) {
  const approveMutation = useApprovePhase();

  const handleAction = async (phaseId: string, action: "approve" | "reject") => {
    await approveMutation.mutateAsync({ opportunityId, phaseId, action });
    onPhaseAction?.();
  };

  return (
    <div className="space-y-0">
      {phases.map((phase, i) => {
        const config = statusConfig[phase.status] || statusConfig.pending;
        const Icon = config.icon;
        const isLast = i === phases.length - 1;
        const isActionable = phase.status === "pending_approval";

        return (
          <div key={phase.id} className="flex gap-3">
            {/* Timeline line + dot */}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 shrink-0 transition-colors",
                  phase.status === "completed"
                    ? "bg-green-400/10 border-green-400 text-green-400"
                    : phase.status === "pending_approval"
                    ? "bg-yellow-400/10 border-yellow-400 text-yellow-400"
                    : phase.status === "in_progress"
                    ? "bg-primary-400/10 border-primary-400 text-primary-400"
                    : "bg-[#16161f] border-[#2a2a3d] text-secondary-500"
                )}
              >
                {phase.status === "completed" ? <Check className="w-4 h-4" /> : phase.order}
              </div>
              {!isLast && (
                <div
                  className={cn(
                    "w-0.5 flex-1 min-h-[24px] mt-1",
                    phase.status === "completed" ? "bg-green-400/20" : "bg-[#1e1e2d]"
                  )}
                />
              )}
            </div>

            {/* Content */}
            <div
              className={cn(
                "flex-1 pb-4 rounded-xl p-3 -mt-1 transition-colors",
                isActionable ? "bg-[#16161f] border border-yellow-400/20" : "bg-transparent"
              )}
            >
              <div className="flex items-center justify-between mb-0.5">
                <h4
                  className={cn(
                    "text-sm font-semibold",
                    phase.status === "pending" ? "text-secondary-400" : "text-white"
                  )}
                >
                  {phase.title}
                </h4>
                <span
                  className={cn(
                    "flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium border",
                    config.bg,
                    config.color
                  )}
                >
                  <Icon className={cn("w-3 h-3", phase.status === "in_progress" && "animate-spin")} />
                  {config.label}
                </span>
              </div>
              {phase.agent && (
                <p className="text-xs text-secondary-500">
                  Agente: <span className="text-secondary-300">{phase.agent}</span>
                </p>
              )}
              {phase.description && (
                <p className="text-xs text-secondary-500 mt-0.5">{phase.description}</p>
              )}
              {phaseTimestamp(phase) && (
                <p className="text-[11px] text-secondary-600 mt-0.5">{phaseTimestamp(phase)}</p>
              )}
              {phase.feedback && (
                <p className="text-[11px] text-yellow-400/80 mt-1">
                  Feedback: {phase.feedback}
                </p>
              )}

              {/* Action buttons for pending_approval */}
              {isActionable && (
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => handleAction(phase.id, "approve")}
                    disabled={approveMutation.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-medium hover:bg-green-500/20 transition-colors disabled:opacity-50"
                  >
                    <Check className="w-3 h-3" />
                    Aprobar
                  </button>
                  <button
                    onClick={() => handleAction(phase.id, "reject")}
                    disabled={approveMutation.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium hover:bg-red-500/20 transition-colors disabled:opacity-50"
                  >
                    <AlertCircle className="w-3 h-3" />
                    Rechazar
                  </button>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
