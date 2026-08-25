import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPatch, apiPost } from "@/app/services/api";
import { toastLoading, updateToast, dismissToast } from "@/app/store/toast";
import { handleApiError } from "./useApiError";

export interface Phase {
  id: string;
  number: number;
  title: string;
  agent: string;
  agent_id: string;
  status: "completed" | "pending_approval" | "pending" | "aborted" | "in_progress";
  time?: string;
  started_at?: string;
  completed_at?: string;
}

export interface AgentResult {
  confidence: "Alta" | "Media" | "Baja";
  suggestion: string;
  explanation: string;
  key_data: { label: string; value: string }[];
}

export interface GeneratedFile {
  id: string;
  name: string;
  type: "pdf" | "xlsx" | "csv" | "doc";
  size: string;
  url: string;
  created_at: string;
}

export interface ActivityItem {
  id: string;
  type: "completed" | "file" | "search" | "user" | "car" | "alert" | "agent" | "workflow";
  title: string;
  description: string;
  created_at: string;
  metadata?: string;
}

export interface OpportunityDetail {
  id: string;
  vehicle?: {
    id: string;
    brand?: string | null;
    model?: string | null;
    year?: number | null;
    mileage?: number | null;
    price?: number | null;
    source?: string | null;
    external_id?: string | null;
    url?: string | null;
  } | null;
  score?: number | null;
  estimated_profit?: number | null;
  roi_percentage?: number | null;
  recommendation?: string | null;
  recommendation_label_es?: string | null;
  risk_level?: string | null;
  risk_label_es?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  phases: Phase[];
  current_phase?: number;
  // Compat: campos legacy que el backend no devuelve, se derivan en el cliente
  title?: string;
  brand?: string;
  model?: string;
  year?: number;
  status?: "active" | "pending" | "completed" | "aborted";
  price?: number;
  market_price?: number;
  margin?: number;
  agent_result?: AgentResult;
  files: GeneratedFile[];
  activity_log: ActivityItem[];
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
        queryClient.invalidateQueries({ queryKey: ["dashboardStats"] }),
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