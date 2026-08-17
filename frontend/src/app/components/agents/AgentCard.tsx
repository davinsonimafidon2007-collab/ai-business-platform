"use client";

import { Bot, CheckCircle2, Clock, Zap } from "lucide-react";

interface AgentCardProps {
  name: string;
  role: string;
  description: string;
  status: "active" | "idle" | "busy" | "error";
  tasksCompleted: number;
  avgTime: string;
  successRate: number;
}

const STATUS_CONFIG = {
  active: { label: "Activo", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
  busy: { label: "Ocupado", color: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
  idle: { label: "En espera", color: "bg-secondary-500/10 text-secondary-400 border-secondary-500/20" },
  error: { label: "Error", color: "bg-rose-500/10 text-rose-400 border-rose-500/20" },
};

export function AgentCard({
  name,
  role,
  description,
  status,
  tasksCompleted,
  avgTime,
  successRate,
}: AgentCardProps) {
  const statusInfo = STATUS_CONFIG[status] || STATUS_CONFIG.idle;

  return (
    <div className="p-4 rounded-2xl bg-[#111118] border border-[#1e1e2d] hover:border-[#2a2a3d] transition-all space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-primary-600/10 border border-primary-600/20 flex items-center justify-center text-primary-400">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-white text-base">{name}</h3>
            <p className="text-xs text-secondary-400">{role}</p>
          </div>
        </div>
        <span
          className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${statusInfo.color}`}
        >
          {statusInfo.label}
        </span>
      </div>

      <p className="text-xs text-secondary-300 line-clamp-2">{description}</p>

      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#1e1e2d]">
        <div className="p-2 rounded-xl bg-[#16161f] border border-[#1e1e2d]">
          <div className="flex items-center gap-1 text-[10px] text-secondary-400">
            <CheckCircle2 className="w-3 h-3" /> Tareas
          </div>
          <p className="text-xs font-bold text-white mt-0.5">{tasksCompleted}</p>
        </div>
        <div className="p-2 rounded-xl bg-[#16161f] border border-[#1e1e2d]">
          <div className="flex items-center gap-1 text-[10px] text-secondary-400">
            <Clock className="w-3 h-3" /> T. Medio
          </div>
          <p className="text-xs font-bold text-white mt-0.5">{avgTime}</p>
        </div>
        <div className="p-2 rounded-xl bg-[#16161f] border border-[#1e1e2d]">
          <div className="flex items-center gap-1 text-[10px] text-secondary-400">
            <Zap className="w-3 h-3" /> Éxito
          </div>
          <p className="text-xs font-bold text-emerald-400 mt-0.5">{successRate}%</p>
        </div>
      </div>
    </div>
  );
}
