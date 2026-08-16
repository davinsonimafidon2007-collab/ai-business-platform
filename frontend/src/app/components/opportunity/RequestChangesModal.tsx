"use client";

import { useState } from "react";
import { X, Send } from "lucide-react";
import { useRequestChanges } from "@/app/hooks/useOpportunityDetail";

interface RequestChangesModalProps {
  open: boolean;
  onClose: () => void;
  opportunityId: string;
  phaseId: string;
}

export function RequestChangesModal({ open, onClose, opportunityId, phaseId }: RequestChangesModalProps) {
  const [feedback, setFeedback] = useState("");
  const mutation = useRequestChanges();

  if (!open) return null;

  const handleSubmit = async () => {
    if (!feedback.trim()) return;
    await mutation.mutateAsync({ opportunityId, phaseId, feedback });
    setFeedback("");
    onClose();
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/60 z-50" onClick={onClose} />
      <div className="fixed inset-x-4 top-1/2 -translate-y-1/2 max-w-md mx-auto z-50 bg-[#111118] border border-[#1e1e2d] rounded-2xl p-5 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-white">Solicitar cambios</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg text-secondary-400 hover:text-white hover:bg-[#1a1a24]">
            <X className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-secondary-500 mb-3">
          Describe qué cambios necesita el agente para continuar.
        </p>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Ej: Revisa el precio de mercado, parece desactualizado..."
          rows={4}
          className="w-full p-3 rounded-xl bg-[#16161f] border border-[#1e1e2d] text-sm text-white placeholder:text-secondary-600 focus:outline-none focus:border-primary-600 focus:ring-1 focus:ring-primary-600/30 resize-none transition-all"
        />
        <div className="flex gap-3 mt-4">
          <button
            onClick={onClose}
            className="flex-1 h-10 rounded-xl border border-[#1e1e2d] text-secondary-300 hover:text-white text-sm font-medium transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={!feedback.trim() || mutation.isPending}
            className="flex-1 flex items-center justify-center gap-2 h-10 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-sm font-semibold transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
            {mutation.isPending ? "Enviando..." : "Enviar"}
          </button>
        </div>
      </div>
    </>
  );
}
