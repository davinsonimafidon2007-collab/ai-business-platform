"use client";

import { ShieldCheck, UserCheck } from "lucide-react";

export function HumanSupervision() {
  return (
    <div className="rounded-2xl bg-[#111118] border border-[#1e1e2d] p-4 space-y-3">
      <div className="flex items-center gap-2">
        <ShieldCheck className="w-4 h-4 text-emerald-400" />
        <h3 className="text-xs font-semibold text-white uppercase tracking-wider">Supervisión Humana</h3>
      </div>
      <p className="text-xs text-secondary-400 leading-relaxed">
        Las acciones críticas de este workflow requieren aprobación manual para garantizar la seguridad en cada operación.
      </p>
      <div className="flex items-center gap-2 text-[11px] text-emerald-400 bg-emerald-500/10 p-2.5 rounded-xl border border-emerald-500/20">
        <UserCheck className="w-3.5 h-3.5 shrink-0" />
        <span>Modo de supervisión activo</span>
      </div>
    </div>
  );
}
