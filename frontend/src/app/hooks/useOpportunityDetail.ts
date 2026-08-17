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
  title: string;
  brand: string;
  model: string;
  year: number;
  status: "active" | "pending" | "completed" | "aborted";
  price: number;
  market_price: number;
  margin: number;
  phases: Phase[];
  current_phase: number;
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
          variables.action === "approve" ? "Fase aprobada" : "Fase rechazada",
          variables.action === "approve"
            ? "La fase ha sido aprobada y el workflow continúa."
            : "La fase ha sido rechazada. El agente será notificado."
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
      handleApiError(error, variables.action === "approve" ? "aprobar fase" : "rechazar fase");
    },
  });
}

export function useRequestChanges() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ opportunityId, phaseId, feedback }: { opportunityId: string; phaseId: string; feedback: string }) =>
      apiPost(`/opportunities/${opportunityId}/phases/${phaseId}/feedback`, { feedback }),

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