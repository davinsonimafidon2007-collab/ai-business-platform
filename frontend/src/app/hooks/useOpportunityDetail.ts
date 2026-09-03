import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPatch, apiPost } from "@/app/services/api";
import { toastLoading, updateToast, dismissToast } from "@/app/store/toast";
import { handleApiError } from "./useApiError";

/**
 * Contrato real de GET /opportunities/{id} (OpportunityReadDetail en el
 * backend). TASK 4/6 (AUD-014): antes este hook declaraba campos que el
 * backend nunca ha devuelto (title, brand, market_price, margin,
 * current_phase, agent_result, files, activity_log), por lo que la página
 * de detalle renderizaba `undefined` en casi todo. Ahora los tipos
 * reflejan exactamente lo que la API sirve.
 */

export type PhaseStatus =
  | "completed"
  | "pending_approval"
  | "pending"
  | "aborted"
  | "in_progress";

export interface Phase {
  id: string;
  opportunity_id: string;
  title: string;
  description?: string | null;
  status: PhaseStatus;
  agent?: string | null;
  /** Orden dentro del workflow (el backend lo llama `order`, no `number`). */
  order: number;
  started_at?: string | null;
  completed_at?: string | null;
  feedback?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface OpportunityVehicleSummary {
  id: string;
  brand?: string | null;
  model?: string | null;
  year?: number | null;
  mileage?: number | null;
  price?: number | null;
  source?: string | null;
  external_id?: string | null;
  url?: string | null;
}

export interface OpportunityDetail {
  id: string;
  vehicle?: OpportunityVehicleSummary | null;
  score?: number | null;
  estimated_profit?: number | null;
  roi_percentage?: number | null;
  recommendation?: string | null;
  recommendation_label_es?: string | null;
  recommendation_label?: string | null;
  risk_level?: string | null;
  risk_label_es?: string | null;
  risk_label?: string | null;
  /** Confianza 0-100 de los datos (TASK 2). */
  confidence?: number | null;
  /** OPEN | CONVERTED (TASK 3). */
  status?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  phases: Phase[];
}

export function useOpportunityDetail(id: string) {
  return useQuery({
    queryKey: ["opportunity", id],
    queryFn: () => apiGet<OpportunityDetail>(`/opportunities/${id}`),
    staleTime: 10_000,
    enabled: !!id,
  });
}

export function useApprovePhase() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ opportunityId, phaseId, action }: { opportunityId: string; phaseId: string; action: "approve" | "reject" | "request_changes" }) =>
      apiPatch(`/opportunities/${opportunityId}/phases/${phaseId}`, { action }),

    onMutate: async ({ action }) => {
      const toastId = toastLoading(
        action === "approve" ? "Aprobando fase..." : action === "reject" ? "Rechazando fase..." : "Procesando..."
      );
      return { toastId };
    },

    onSuccess: async (_, variables, context) => {
      const { toastId } = context || {};
      if (toastId) {
        updateToast(
          toastId,
          "success",
          variables.action === "approve" ? "Fase aprobada" : variables.action === "reject" ? "Fase rechazada" : "Cambios solicitados",
          variables.action === "approve"
            ? "La fase ha sido aprobada y el workflow continúa."
            : variables.action === "reject"
              ? "La fase ha sido rechazada. El agente será notificado."
              : "Se han enviado los cambios al agente.",
        );
      }

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["opportunity", variables.opportunityId] }),
        queryClient.invalidateQueries({ queryKey: ["opportunities"] }),
        queryClient.invalidateQueries({ queryKey: ["approvals"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
      ]);
    },

    onError: (error, variables, context) => {
      const { toastId } = context || {};
      if (toastId) dismissToast(toastId);
      handleApiError(error, variables.action === "approve" ? "aprobar fase" : variables.action === "reject" ? "rechazar fase" : "procesar fase");
    },
  });
}

export function useRequestChanges() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ opportunityId, phaseId, feedback }: { opportunityId: string; phaseId: string; feedback: string }) =>
      apiPatch(`/opportunities/${opportunityId}/phases/${phaseId}`, { action: "request_changes", feedback }),

    onMutate: async () => {
      const toastId = toastLoading("Enviando feedback...");
      return { toastId };
    },

    onSuccess: async (_, variables, context) => {
      const { toastId } = context || {};
      if (toastId) {
        updateToast(toastId, "success", "Feedback enviado", "El agente recibirá tus comentarios y actuará en consecuencia.");
      }
      await queryClient.invalidateQueries({ queryKey: ["opportunity", variables.opportunityId] });
    },

    onError: (error, _, context) => {
      const { toastId } = context || {};
      if (toastId) dismissToast(toastId);
      handleApiError(error, "enviar feedback");
    },
  });
}