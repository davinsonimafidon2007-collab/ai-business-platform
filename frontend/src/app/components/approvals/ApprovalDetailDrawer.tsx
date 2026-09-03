"use client";

import { X, FileText, CheckCircle2, XCircle } from "lucide-react";

interface FileItem {
  name: string;
  type: "pdf" | "xlsx" | "doc";
  size: string;
}

interface ApprovalDetailData {
  title: string;
  subtitle: string;
  status: string;
  confidence: string;
  suggestion: string;
  explanation: string;
  files: FileItem[];
}

interface ApprovalDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  data?: ApprovalDetailData;
}

export function ApprovalDetailDrawer({
  open,
  onClose,
  data,
}: ApprovalDetailDrawerProps) {
  if (!open || !data) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="approval-drawer-title"
        className="w-full max-w-lg bg-[#111118] border-l border-[#1e1e2d] h-full overflow-y-auto p-6 space-y-6 flex flex-col justify-between"
      >
        <div className="space-y-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 id="approval-drawer-title" className="text-lg font-bold text-white">{data.title}</h2>
              <p className="text-xs text-secondary-400 mt-0.5">{data.subtitle}</p>
            </div>
            <button
              onClick={onClose}
              aria-label="Cerrar panel"
              className="p-1.5 rounded-lg text-secondary-400 hover:text-white hover:bg-[#16161f] transition-colors"
            >
              <X className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>

          <div className="p-4 rounded-xl bg-[#16161f] border border-[#1e1e2d] space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-secondary-400">Confianza del análisis</span>
              <span className="font-semibold text-emerald-400">{data.confidence}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-secondary-400">Sugerencia del sistema</span>
              <span className="font-semibold text-primary-400">{data.suggestion}</span>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-secondary-400 uppercase tracking-wider">
              Explicación del análisis
            </h3>
            <p className="text-sm text-secondary-200 bg-[#16161f] p-4 rounded-xl border border-[#1e1e2d] leading-relaxed">
              {data.explanation}
            </p>
          </div>

          {data.files.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-secondary-400 uppercase tracking-wider">
                Documentos adjuntos
              </h3>
              <div className="space-y-2">
                {data.files.map((file, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 rounded-xl bg-[#16161f] border border-[#1e1e2d]"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="w-4 h-4 text-primary-400" />
                      <span className="text-xs font-medium text-white">{file.name}</span>
                    </div>
                    <span className="text-xs text-secondary-500">{file.size}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-3 pt-4 border-t border-[#1e1e2d]">
          <button
            onClick={onClose}
            className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-sm font-semibold transition-colors"
          >
            <XCircle className="w-4 h-4" />
            Rechazar
          </button>
          <button
            onClick={onClose}
            className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold transition-colors"
          >
            <CheckCircle2 className="w-4 h-4" />
            Aprobar
          </button>
        </div>
      </div>
    </div>
  );
}
