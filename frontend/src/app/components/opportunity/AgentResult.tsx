"use client";

import { Sparkles, CheckCircle2 } from "lucide-react";

interface AgentResultProps {
  confidence: "Alta" | "Media" | "Baja";
  suggestion: string;
  explanation: string;
  keyData: { label: string; value: string }[];
}

export function AgentResult({ confidence, suggestion, explanation, keyData }: AgentResultProps) {
  return (
    <div className="rounded-2xl bg-[#111118] border border-[#1e1e2d] p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-primary-600/10 border border-primary-600/20 flex items-center justify-center text-primary-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-semibold text-white">Análisis del Agente</h3>
        </div>
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          Confianza: {confidence}
        </span>
      </div>

      <div className="p-3 rounded-xl bg-[#16161f] border border-[#1e1e2d] space-y-2">
        <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider">Recomendación</p>
        <p className="text-xs text-white font-medium">{suggestion}</p>
        <p className="text-xs text-secondary-300 leading-relaxed">{explanation}</p>
      </div>

      {keyData && keyData.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {keyData.map((item, idx) => (
            <div key={idx} className="p-2.5 rounded-xl bg-[#16161f] border border-[#1e1e2d]">
              <span className="text-[10px] text-secondary-500 block truncate">{item.label}</span>
              <span className="text-xs font-bold text-white mt-0.5 block truncate">{item.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
