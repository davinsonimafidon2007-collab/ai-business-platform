"use client";

import { Check, X, MessageSquareDiff } from "lucide-react";

interface ApprovalActionsProps {
  onApprove: () => void;
  onReject: () => void;
  onRequestChanges: () => void;
  isLoading?: boolean;
}

export function ApprovalActions({ onApprove, onReject, onRequestChanges, isLoading }: ApprovalActionsProps) {
  return (
    <div className="space-y-3">
      <div className="flex gap-3">
        <button
          onClick={onApprove}
          disabled={isLoading}
          className="flex-1 flex items-center justify-center gap-2 h-11 rounded-xl bg-green-500 hover:bg-green-600 disabled:opacity-50 text-white font-semibold text-sm transition-colors active:scale-[0.98]"
        >
          <Check className="w-4 h-4" />
          {isLoading ? "Procesando..." : "Aprobar"}
        </button>
        <button
          onClick={onReject}
          disabled={isLoading}
          className="flex-1 flex items-center justify-center gap-2 h-11 rounded-xl bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white font-semibold text-sm transition-colors active:scale-[0.98]"
        >
          <X className="w-4 h-4" />
          {isLoading ? "Procesando..." : "Rechazar"}
        </button>
      </div>
      <button
        onClick={onRequestChanges}
        disabled={isLoading}
        className="w-full flex items-center justify-center gap-2 h-10 rounded-xl border border-[#2a2a3d] text-secondary-300 hover:text-white hover:bg-[#1a1a24] disabled:opacity-50 text-sm font-medium transition-colors"
      >
        <MessageSquareDiff className="w-4 h-4" />
        Solicitar cambios
      </button>
    </div>
  );
}
